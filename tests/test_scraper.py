"""Unit tests for the news article URL scraper (SCR-01)."""

import socket
from unittest.mock import Mock, patch

import pytest
import requests

from backend.scraper import (
    MAX_RESPONSE_BYTES,
    EmptyArticleError,
    InvalidURLError,
    ScrapeFetchError,
    extract_article_text,
    validate_url,
)

PUBLIC_DNS_RESULT = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _make_mock_response(
    html: str,
    url: str = "https://news.example.com/article",
    content_type: str = "text/html; charset=utf-8",
    status_error: Exception | None = None,
) -> Mock:
    """Create a mocked requests.Response object."""
    resp = Mock()
    resp.url = url
    resp.status_code = 200 if status_error is None else 404
    resp.headers = {"Content-Type": content_type}
    resp.encoding = "utf-8"
    resp.iter_content.return_value = [html.encode("utf-8")]
    if status_error is not None:
        resp.raise_for_status.side_effect = status_error
    return resp


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "   ",
        "ftp://example.com/news",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https:///missing-host",
        "http://localhost/article",
        "http://sub.localhost/article",
        "http://127.0.0.1:8000/docs",
        "http://10.0.0.1/internal",
        "http://172.16.0.5/internal",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
    ],
)
def test_validate_url_rejects_invalid_and_ssrf_urls(bad_url: str) -> None:
    with pytest.raises(InvalidURLError):
        validate_url(bad_url)


def test_validate_url_rejects_dns_resolving_to_private_ip() -> None:
    private_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.0.10", 0))]
    with patch("backend.scraper.socket.getaddrinfo", return_value=private_dns):
        with pytest.raises(InvalidURLError):
            validate_url("https://internal.example.com/story")


def test_validate_url_raises_fetch_error_on_dns_failure() -> None:
    with patch("backend.scraper.socket.getaddrinfo", side_effect=socket.gaierror("DNS failed")):
        with pytest.raises(ScrapeFetchError):
            validate_url("https://nonexistent.example.invalid/story")


def test_validate_url_accepts_and_strips_public_url() -> None:
    with patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT):
        assert validate_url("  https://example.com/news  ") == "https://example.com/news"


def test_extract_article_text_semantic_article_and_dom_cleaning() -> None:
    html = """
    <html>
      <head>
        <title>Site Name - Fallback</title>
        <meta property="og:title" content="  Global Summit   Reaches Climate Accord  ">
      </head>
      <body>
        <header><nav><p>Home World Politics Business</p></nav></header>
        <div class="cookie-banner"><p>Please accept all cookies before continuing to read.</p></div>
        <article>
          <p>Read more</p>
          <p>Delegates from more than one hundred nations signed an ambitious climate framework in Geneva today.</p>
          <script>window.alert("xss")</script>
          <aside><p>Sponsored advertisement link that should be removed from text.</p></aside>
          <p>Economic ministers pledged new clean energy investments over the coming decade to stabilize emissions.</p>
        </article>
        <footer><p>Copyright 2026 Example News Network All Rights Reserved.</p></footer>
      </body>
    </html>
    """
    mock_resp = _make_mock_response(html)

    with (
        patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT),
        patch("backend.scraper.requests.get", return_value=mock_resp) as mock_get,
    ):
        result = extract_article_text("https://news.example.com/article")

    assert result["url"] == "https://news.example.com/article"
    assert result["title"] == "Global Summit Reaches Climate Accord"
    assert "Delegates from more than one hundred nations" in result["text"]
    assert "Economic ministers pledged new clean energy investments" in result["text"]
    assert "Read more" not in result["text"]
    assert "Please accept all cookies" not in result["text"]
    assert "Sponsored advertisement" not in result["text"]
    assert "Copyright 2026" not in result["text"]
    assert "window.alert" not in result["text"]
    assert mock_get.call_args.kwargs["timeout"] == (5, 10)
    mock_resp.close.assert_called_once()


def test_extract_article_text_fallback_paragraphs_and_h1_title() -> None:
    html = """
    <html>
      <head><title>Site Title</title></head>
      <body>
        <header><h1>Local Transit Expansion Approved by City Council</h1></header>
        <div class="content">
          <p>City council members voted overwhelmingly on Tuesday evening to fund two new light rail corridors.</p>
          <p>Construction is scheduled to begin next spring and will connect eastern neighborhoods to downtown.</p>
        </div>
      </body>
    </html>
    """
    mock_resp = _make_mock_response(html)

    with (
        patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT),
        patch("backend.scraper.requests.get", return_value=mock_resp),
    ):
        result = extract_article_text("https://news.example.com/transit")

    assert result["title"] == "Local Transit Expansion Approved by City Council"
    assert "City council members voted overwhelmingly" in result["text"]
    assert "Construction is scheduled to begin" in result["text"]


def test_extract_article_text_rejects_short_or_paywalled_page() -> None:
    html = "<html><head><title>Paywall</title></head><body><p>Subscribe now to read the full story.</p></body></html>"
    mock_resp = _make_mock_response(html)

    with (
        patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT),
        patch("backend.scraper.requests.get", return_value=mock_resp),
    ):
        with pytest.raises(EmptyArticleError):
            extract_article_text("https://news.example.com/paywall")


def test_extract_article_text_handles_timeout_and_http_errors() -> None:
    with patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT):
        with patch("backend.scraper.requests.get", side_effect=requests.Timeout("timed out")):
            with pytest.raises(ScrapeFetchError):
                extract_article_text("https://news.example.com/slow")

        err_resp = _make_mock_response("", status_error=requests.HTTPError("403 Forbidden"))
        with patch("backend.scraper.requests.get", return_value=err_resp):
            with pytest.raises(ScrapeFetchError):
                extract_article_text("https://news.example.com/forbidden")


def test_extract_article_text_rejects_non_html_and_oversized_payload() -> None:
    pdf_resp = _make_mock_response("%PDF-1.4", content_type="application/pdf")
    big_resp = _make_mock_response("<html></html>")
    big_resp.iter_content.return_value = [b"a" * (MAX_RESPONSE_BYTES + 1)]

    with patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT):
        with patch("backend.scraper.requests.get", return_value=pdf_resp):
            with pytest.raises(ScrapeFetchError):
                extract_article_text("https://news.example.com/report.pdf")

        with patch("backend.scraper.requests.get", return_value=big_resp):
            with pytest.raises(ScrapeFetchError):
                extract_article_text("https://news.example.com/huge")


def test_extract_article_text_blocks_ssrf_redirect() -> None:
    redir_resp = _make_mock_response("<html></html>", url="http://127.0.0.1/secret")
    with (
        patch("backend.scraper.socket.getaddrinfo", return_value=PUBLIC_DNS_RESULT),
        patch("backend.scraper.requests.get", return_value=redir_resp),
    ):
        with pytest.raises(InvalidURLError):
            extract_article_text("https://news.example.com/redirect")
