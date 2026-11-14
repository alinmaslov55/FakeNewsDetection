"""Web scraping logic for extracting news article text from URLs using BeautifulSoup."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from bs4 import BeautifulSoup, FeatureNotFound, Tag
import requests

ALLOWED_SCHEMES = {"http", "https"}
REQUEST_TIMEOUT = (5, 10)  # (connect_timeout, read_timeout) in seconds
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
MIN_PARAGRAPH_WORDS = 5
MIN_ARTICLE_CHARS = 100
MIN_ARTICLE_WORDS = 20
NOISE_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
    "svg",
    "button",
)
NOISE_ATTR_PATTERN = re.compile(
    r"\b(?:cookie[-_]?(?:banner|consent|notice)|ad[-_]?(?:banner|slot|wrapper|container)|"
    r"advertisement|newsletter[-_]?(?:signup|box)|social[-_]?share)\b",
    re.IGNORECASE,
)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ScraperError(Exception):
    """Base exception for all news article scraping errors."""


class InvalidURLError(ScraperError):
    """Raised when a URL is malformed, uses a disallowed scheme, or targets a restricted IP."""


class ScrapeFetchError(ScraperError):
    """Raised when fetching the target URL fails due to network, DNS, timeout, or HTTP errors."""


class EmptyArticleError(ScraperError):
    """Raised when a page is fetched but yields insufficient article body text."""


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if the IP belongs to loopback, private, link-local, or other non-public ranges."""
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    # Check IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
    ipv4_mapped = getattr(ip, "ipv4_mapped", None)
    if ipv4_mapped is not None:
        return _is_disallowed_ip(ipv4_mapped)

    return False


def validate_url(url: str) -> str:
    """
    Validate URL syntax, enforce http/https schemes, and block SSRF targets.

    Args:
        url: Raw URL string submitted by the user or redirect target.

    Returns:
        Normalized, stripped URL string if valid and safe to fetch.

    Raises:
        InvalidURLError: If the URL is empty, malformed, uses a non-HTTP(S) scheme,
            or resolves to a loopback, private, link-local, or reserved IP address.
        ScrapeFetchError: If DNS resolution fails for the target hostname.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidURLError("URL must be a non-empty string.")

    cleaned_url = url.strip()
    parsed = urlparse(cleaned_url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLError("URL must include a valid hostname.")

    normalized_host = hostname.lower().rstrip(".")
    if normalized_host == "localhost" or normalized_host.endswith(".localhost"):
        raise InvalidURLError("Access to localhost URLs is not allowed.")

    # Fast check if the hostname is already an IP literal
    try:
        ip_literal = ipaddress.ip_address(hostname.split("%")[0])
    except ValueError:
        ip_literal = None

    if ip_literal is not None:
        if _is_disallowed_ip(ip_literal):
            raise InvalidURLError(
                f"Access to private or restricted IP address '{ip_literal}' is not allowed."
            )
        return cleaned_url

    # Resolve domain name and verify all returned IP addresses are public
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ScrapeFetchError(f"Could not resolve hostname '{hostname}': {exc}") from exc

    if not addr_info:
        raise ScrapeFetchError(f"No IP addresses resolved for hostname '{hostname}'.")

    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0].split("%")[0]
        try:
            resolved_ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if _is_disallowed_ip(resolved_ip):
            raise InvalidURLError(
                f"Hostname '{hostname}' resolves to restricted IP address '{resolved_ip}'."
            )

    return cleaned_url


def _fetch_html(url: str) -> tuple[str, str]:
    """
    Fetch raw HTML from a validated URL with timeouts, size limits, and content checks.

    Returns:
        Tuple of (html_text, final_resolved_url).
    """
    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
    except requests.Timeout as exc:
        raise ScrapeFetchError(f"Request timed out while fetching '{url}'.") from exc
    except requests.RequestException as exc:
        raise ScrapeFetchError(f"Network error while fetching '{url}': {exc}") from exc

    try:
        final_url = response.url or url
        if final_url != url:
            validate_url(final_url)

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = response.status_code
            raise ScrapeFetchError(
                f"Upstream server returned HTTP {status_code} for '{final_url}'."
            ) from exc

        raw_content_type = response.headers.get("Content-Type", "")
        media_type = raw_content_type.split(";")[0].strip().lower()
        if media_type and media_type not in ALLOWED_CONTENT_TYPES:
            raise ScrapeFetchError(
                f"Unsupported Content-Type '{media_type}'. Expected an HTML document."
            )

        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_RESPONSE_BYTES:
                    raise ScrapeFetchError(
                        f"Response size exceeds the {MAX_RESPONSE_BYTES // (1024 * 1024)} MB limit."
                    )
            except ValueError:
                pass

        chunks: list[bytes] = []
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total_bytes += len(chunk)
            if total_bytes > MAX_RESPONSE_BYTES:
                raise ScrapeFetchError(
                    f"Response payload exceeded the {MAX_RESPONSE_BYTES // (1024 * 1024)} MB limit."
                )
            chunks.append(chunk)

        raw_bytes = b"".join(chunks)
        encoding = response.encoding or getattr(response, "apparent_encoding", None) or "utf-8"
        html_text = raw_bytes.decode(encoding, errors="replace")
        return html_text, final_url
    finally:
        response.close()


def _parse_html(html: str) -> BeautifulSoup:
    """Parse HTML string using lxml with html.parser fallback."""
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


def _extract_title(soup: BeautifulSoup) -> str:
    """
    Extract article headline via OpenGraph, Twitter Card, h1, or document title.
    """
    candidates = [
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "twitter:title"}),
    ]
    for meta in candidates:
        if meta is not None:
            content = meta.get("content")
            if isinstance(content, str) and content.strip():
                return re.sub(r"\s+", " ", content).strip()

    for tag_name in ("h1", "title"):
        tag = soup.find(tag_name)
        if tag is not None:
            text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()
            if text:
                return text

    return ""


def _clean_dom(soup: BeautifulSoup) -> None:
    """Decompose non-article DOM clutter such as scripts, navbars, footers, and ad banners."""
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    protected_tags = {"html", "body", "article", "main"}
    for tag in list(soup.find_all(True)):
        if getattr(tag, "attrs", None) is None or tag.name in protected_tags:
            continue
        classes = tag.get("class") or []
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
        tag_id = str(tag.get("id") or "")
        if NOISE_ATTR_PATTERN.search(class_str) or NOISE_ATTR_PATTERN.search(tag_id):
            tag.decompose()


def _collect_paragraphs(root: Tag | BeautifulSoup) -> str:
    """Collect and join meaningful <p> paragraphs, skipping short boilerplate fragments."""
    paragraphs: list[str] = []
    seen: set[str] = set()

    for p in root.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()
        if not text or len(text.split()) < MIN_PARAGRAPH_WORDS:
            continue
        if text not in seen:
            seen.add(text)
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


def _meets_length_threshold(text: str) -> bool:
    """Return True if extracted text satisfies minimum character and word count thresholds."""
    return len(text) >= MIN_ARTICLE_CHARS and len(text.split()) >= MIN_ARTICLE_WORDS


def _extract_body_text(soup: BeautifulSoup) -> str:
    """
    Extract main article body text prioritizing semantic containers (<article>, <main>,
    [role='main']), falling back to document-wide <p> aggregation.
    """
    semantic_containers = [
        soup.find("article"),
        soup.find("main"),
        soup.find(attrs={"role": "main"}),
    ]

    for container in semantic_containers:
        if container is not None:
            candidate = _collect_paragraphs(container)
            if _meets_length_threshold(candidate):
                return candidate

    fallback_root = soup.body if soup.body is not None else soup
    return _collect_paragraphs(fallback_root)


def extract_article_text(url: str) -> dict[str, str]:
    """
    Extract article title and main body text from a given URL.

    Args:
        url: The web address of the news article.

    Returns:
        dict: Containing 'url', 'title', and 'text'.

    Raises:
        InvalidURLError: If URL syntax, scheme, or resolved IP is disallowed.
        ScrapeFetchError: If fetching the page fails due to network, timeout, or HTTP error.
        EmptyArticleError: If extracted article body is below minimum length thresholds.
    """
    validated_url = validate_url(url)
    html, final_url = _fetch_html(validated_url)
    soup = _parse_html(html)
    title = _extract_title(soup)
    _clean_dom(soup)
    body_text = _extract_body_text(soup)

    if not _meets_length_threshold(body_text):
        raise EmptyArticleError(
            "Could not extract sufficient article text from this page "
            "(it may be paywalled, empty, or require JavaScript rendering)."
        )

    return {
        "url": final_url,
        "title": title,
        "text": body_text,
    }
