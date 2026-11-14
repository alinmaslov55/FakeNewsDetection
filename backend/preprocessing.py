"""Shared text preprocessing and linguistic normalization for training and inference"""

from __future__ import annotations

from functools import lru_cache
import html
import re
import unicodedata

from nltk.corpus import stopwords
from nltk.data import find as nltk_find
from nltk.downloader import download as nltk_download
from nltk.stem import WordNetLemmatizer

# Negation cues preserved from stopword removal to retain semantic polarity
NEGATION_WORDS = frozenset(
    {
        "no",
        "nor",
        "not",
        "never",
        "neither",
        "none",
        "nothing",
        "nowhere",
        "without",
        "against",
    }
)

# Precompiled patterns for linear-time cleaning
HTML_TAG_RE = re.compile(r"<[^>]+>")
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
DATELINE_RE = re.compile(
    r"^(?:[^—–\n-]{0,100}\s*)?\((?:Reuters|AP|AFP|Bloomberg)\)\s*[-—–:]?\s*",
    re.IGNORECASE | re.MULTILINE,
)
WIRE_BRAND_RE = re.compile(r"\breuters\b", re.IGNORECASE)
CONTRACTIONS_RE = re.compile(
    r"\b(won|can)('|\u2019)t\b|n('|\u2019)t\b",
    re.IGNORECASE,
)
NON_ALPHA_RE = re.compile(r"[^a-z\s]+")
WHITESPACE_RE = re.compile(r"\s+")

_REQUIRED_NLTK_RESOURCES = (
    ("corpora/stopwords", "stopwords"),
    ("corpora/wordnet", "wordnet"),
)


def ensure_nltk_resources(*, download_if_missing: bool = False) -> None:
    """Verify required NLTK corpora are available, optionally downloading them."""
    for resource_path, package_name in _REQUIRED_NLTK_RESOURCES:
        try:
            nltk_find(resource_path)
        except LookupError as exc:
            if not download_if_missing:
                raise RuntimeError(
                    f"Missing NLTK resource '{package_name}'. "
                    f"Run: python -m nltk.downloader {package_name}"
                ) from exc
            nltk_download(package_name, quiet=True)


def _replace_contraction(match: re.Match[str]) -> str:
    """Expand negative contractions so 'not' is preserved prior to punctuation stripping."""
    matched = match.group(0).lower()
    if matched.startswith("won"):
        return "will not"
    if matched.startswith("can"):
        return "can not"
    return " not"


@lru_cache(maxsize=1)
def _get_stopwords() -> frozenset[str]:
    """Return English stopwords minus polarity-bearing negation words."""
    ensure_nltk_resources(download_if_missing=False)
    words = set(stopwords.words("english"))
    return frozenset(words - NEGATION_WORDS)


@lru_cache(maxsize=1)
def _get_lemmatizer() -> WordNetLemmatizer:
    """Return a cached WordNetLemmatizer warmed up against WordNet."""
    ensure_nltk_resources(download_if_missing=False)
    lemmatizer = WordNetLemmatizer()
    # Trigger WordNet corpus load once
    lemmatizer.lemmatize("news")
    return lemmatizer


@lru_cache(maxsize=50_000)
def _lemmatize_token(token: str) -> str:
    """Lemmatize a single lowercase alphabetic token with O(1) cache hit after first sight."""
    lemmatizer = _get_lemmatizer()
    lemma = lemmatizer.lemmatize(token, pos="n")
    if lemma == token:
        lemma = lemmatizer.lemmatize(token, pos="v")
    return lemma


def warmup() -> None:
    """Preload NLTK stopwords and WordNet lemmatizer into memory."""
    _get_stopwords()
    _get_lemmatizer()


def preprocess_text(
    text: str | None,
    *,
    strip_wire_brand: bool = True,
) -> str:
    """
    Clean and normalize raw news text into a space-separated string of lemmas.

    Steps:
      1. Decode HTML entities and strip markup tags.
      2. Remove wire-service dateline prefixes (DAT-01 leakage) and optional 'Reuters' mentions.
      3. Strip embedded URLs and email addresses.
      4. Normalize Unicode and expand negative contractions (e.g. "don't" -> "do not").
      5. Lowercase, strip punctuation/digits/non-ASCII, and collapse whitespace.
      6. Filter English stopwords (preserving negations) and lemmatize tokens.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    cleaned = html.unescape(text)
    cleaned = HTML_TAG_RE.sub(" ", cleaned)

    cleaned = DATELINE_RE.sub(" ", cleaned)
    if strip_wire_brand:
        cleaned = WIRE_BRAND_RE.sub(" ", cleaned)

    cleaned = URL_RE.sub(" ", cleaned)
    cleaned = EMAIL_RE.sub(" ", cleaned)

    # Normalize accents/diacritics (e.g. "café" -> "cafe") before stripping non-ASCII
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = CONTRACTIONS_RE.sub(_replace_contraction, cleaned)

    cleaned = cleaned.lower()
    cleaned = NON_ALPHA_RE.sub(" ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()

    if not cleaned:
        return ""

    stop_words = _get_stopwords()
    tokens = [
        _lemmatize_token(tok)
        for tok in cleaned.split(" ")
        if len(tok) >= 2 and tok not in stop_words
    ]
    return " ".join(tokens)
