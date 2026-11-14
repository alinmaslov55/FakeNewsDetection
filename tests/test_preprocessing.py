"""Unit and performance tests for text preprocessing module."""

from __future__ import annotations

import time
import pytest

from backend.preprocessing import preprocess_text, warmup


def test_preprocess_is_deterministic():
    sample = "Breaking Report: Scientists studied global climate shifts in 2025."
    first = preprocess_text(sample)
    second = preprocess_text(sample)
    assert first == second
    assert first != ""


def test_strips_html_tags_entities_urls_and_emails():
    raw = (
        "<p>Read &amp; verify at https://example.com/news?id=42 or "
        "www.fake-news.org! Contact tips@example.org for more details.</p>"
    )
    cleaned = preprocess_text(raw)

    assert "http" not in cleaned
    assert "example" not in cleaned
    assert "tips" not in cleaned
    assert "amp" not in cleaned
    assert "<p>" not in cleaned
    assert "read" in cleaned
    assert "verify" in cleaned
    assert "detail" in cleaned


@pytest.mark.parametrize(
    "raw",
    [
        "WASHINGTON (Reuters) - Lawmakers voted on the budget bill Tuesday.",
        "Senate passes new legislation\n\nLONDON (Reuters) - Markets rallied early.",
        "NEW YORK (AP) — City officials announced transit upgrades.",
        "PARIS (AFP): Economic ministers concluded talks.",
    ],
)
def test_strips_wire_service_datelines_and_reuters_leakage(raw: str):
    cleaned = preprocess_text(raw)
    tokens = cleaned.split()

    assert "reuters" not in tokens
    assert "washington" not in tokens
    assert "london" not in tokens
    assert "paris" not in tokens
    assert len(tokens) > 0


def test_can_preserve_wire_brand_when_configured():
    raw = "Independent analysts cited Reuters data in their report."
    assert "reuters" not in preprocess_text(raw, strip_wire_brand=True).split()
    assert "reuters" in preprocess_text(raw, strip_wire_brand=False).split()


def test_removes_stopwords_and_preserves_negations():
    raw = "This is not a real report and the claims were never verified; officials don't agree."
    tokens = preprocess_text(raw).split()

    for stopword in ("this", "is", "and", "the", "were"):
        assert stopword not in tokens

    assert "not" in tokens
    assert "never" in tokens
    assert "agree" in tokens


def test_lemmatizes_inflected_words():
    raw = "Researchers were studying multiple fabricated stories and running simulations."
    tokens = preprocess_text(raw).split()

    assert "researcher" in tokens
    assert "study" in tokens
    assert "story" in tokens
    assert "run" in tokens
    assert "simulation" in tokens


@pytest.mark.parametrize("empty_input", [None, "", "   \n\t  ", "12345 !!! ???"])
def test_handles_empty_and_non_text_inputs_gracefully(empty_input):
    assert preprocess_text(empty_input) == ""


def test_handles_non_ascii_and_emojis():
    raw = "SHOCKING Fake news spreads rapidly across café networks…"
    cleaned = preprocess_text(raw)
    tokens = cleaned.split()

    assert "shock" in tokens
    assert "fake" in tokens
    assert "news" in tokens
    assert "spread" in tokens
    assert "cafe" in tokens


def test_handles_very_long_article():
    long_article = ("WASHINGTON (Reuters) - Officials debated economic policy reforms. " * 400)
    cleaned = preprocess_text(long_article)
    assert len(cleaned) > 0
    assert "reuters" not in cleaned.split()


def test_executes_under_50ms_for_1000_word_article():
    warmup()
    base_sentence = (
        "Lawmakers argued that economic policies were not working during hearings "
        "while independent researchers published detailed studies analyzing inflation. "
    )
    # ~20 words * 50 = ~1,000 words
    article_1000_words = base_sentence * 50

    start = time.perf_counter()
    result = preprocess_text(article_1000_words)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(result) > 0
    assert elapsed_ms < 50.0, f"Expected < 50ms, took {elapsed_ms:.2f}ms"
