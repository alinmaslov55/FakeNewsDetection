"""Unit tests for model loading, credibility inference, and confidence scoring (MLP-02)."""

from __future__ import annotations

from pathlib import Path
import math
import time
import warnings
from unittest.mock import Mock, patch

import joblib
import numpy as np
import pytest
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, PassiveAggressiveClassifier
from sklearn.pipeline import Pipeline

from backend.predictor import (
    ModelNotLoadedError,
    clear_model_cache,
    is_model_loaded,
    load_model,
    predict_credibility,
)


def _build_sample_artifact(tmp_path: Path) -> Path:
    """Train a tiny TF-IDF + LogisticRegression artifact and serialize it for tests."""
    texts = [
        "central bank announced benchmark interest rate unchanged quarterly inflation data",
        "parliament passed annual infrastructure budget bill after committee review",
        "ministry published official employment statistics report for third quarter",
        "shocking leaked secret global elite hiding miracle cure doctors hate",
        "unbelievable breaking scandal video deleted mainstream media before election",
        "secret conspiracy exposed urgent share before internet censorship deletes post",
    ]
    labels = [1, 1, 1, 0, 0, 0]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    classifier = LogisticRegression(random_state=42)
    pipeline = Pipeline([("tfidf", vectorizer), ("clf", classifier)])
    pipeline.fit(texts, labels)

    artifact = {
        "pipeline": pipeline,
        "vectorizer": pipeline.named_steps["tfidf"],
        "classifier": pipeline.named_steps["clf"],
        "classes": {0: "FAKE", 1: "REAL"},
        "metadata": {"metrics": {"f1": 1.0}},
    }

    model_path = tmp_path / "model.pkl"
    joblib.dump(artifact, model_path)
    return model_path


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_model_cache()
    yield
    clear_model_cache()


def test_load_model_missing_file_raises_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing_model.pkl"
    assert is_model_loaded(missing) is False
    with pytest.raises(ModelNotLoadedError, match="not found"):
        load_model(missing)


@pytest.mark.parametrize(
    "bad_payload",
    [
        "not-a-dict",
        {"pipeline": Mock()},
        {
            "pipeline": object(),  # missing predict_proba
            "vectorizer": Mock(),
            "classifier": Mock(),
            "classes": {0: "FAKE", 1: "REAL"},
        },
    ],
)
def test_load_model_invalid_schema_raises_error(tmp_path: Path, bad_payload: object) -> None:
    pkl_path = tmp_path / "bad.pkl"
    pkl_path.write_bytes(b"placeholder")

    with patch("backend.predictor.joblib.load", return_value=bad_payload):
        with pytest.raises(ModelNotLoadedError):
            load_model(pkl_path)


def test_load_model_caches_singleton_across_calls(tmp_path: Path) -> None:
    model_path = _build_sample_artifact(tmp_path)

    with (
        patch("backend.predictor.joblib.load", wraps=joblib.load) as spy_load,
        patch("backend.predictor.warmup") as mock_warmup,
    ):
        first = load_model(model_path)
        second = load_model(model_path)

    assert first is second
    assert spy_load.call_count == 1
    assert mock_warmup.call_count == 1
    assert is_model_loaded(model_path) is True


@pytest.mark.parametrize("bad_text", ["", "   ", "only three words"])
def test_predict_credibility_rejects_empty_and_short_inputs(
    tmp_path: Path, bad_text: str
) -> None:
    model_path = _build_sample_artifact(tmp_path)

    with (
        patch("backend.predictor.MODEL_PATH", model_path),
        patch("backend.predictor.warmup"),
        patch("backend.predictor.preprocess_text", side_effect=lambda s: " ".join(s.lower().split())),
    ):
        with pytest.raises(ValueError):
            predict_credibility(bad_text)


def test_predict_credibility_returns_verdict_confidence_and_runs_under_100ms(
    tmp_path: Path,
) -> None:
    model_path = _build_sample_artifact(tmp_path)
    real_article = (
        "The central bank announced Thursday that benchmark interest rates remain unchanged "
        "following quarterly inflation data published by the statistics ministry."
    )
    fake_article = (
        "SHOCKING LEAKED SECRET: Global elites are hiding this miracle cure before "
        "mainstream media deletes this scandal video forever!"
    )

    with (
        patch("backend.predictor.MODEL_PATH", model_path),
        patch("backend.predictor.warmup"),
        patch("backend.predictor.preprocess_text", side_effect=lambda s: " ".join(s.lower().split())),
    ):
        # Warm up cached load
        first_res = predict_credibility(real_article)

        start = time.perf_counter()
        second_res = predict_credibility(real_article)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        fake_res = predict_credibility(fake_article)

    assert first_res == second_res
    assert first_res["verdict"] == "REAL"
    assert fake_res["verdict"] == "FAKE"

    for res in (first_res, fake_res):
        assert res["verdict"] in ("REAL", "FAKE")
        assert isinstance(res["confidence"], float)
        assert 0.0 <= res["confidence"] <= 1.0
        assert isinstance(res["highlights"], list)

    assert elapsed_ms < 100.0, f"Expected inference < 100ms, took {elapsed_ms:.2f}ms"


def test_predict_credibility_rejects_non_finite_probability() -> None:
    mock_pipe = Mock()
    mock_pipe.classes_ = np.array([0, 1])
    mock_pipe.predict_proba.return_value = np.array([[float("nan"), 0.5]])
    mock_artifact = {
        "pipeline": mock_pipe,
        "vectorizer": Mock(),
        "classifier": Mock(),
        "classes": {0: "FAKE", 1: "REAL"},
    }

    with (
        patch("backend.predictor.load_model", return_value=mock_artifact),
        patch("backend.predictor.preprocess_text", return_value="one two three four five six"),
    ):
        with pytest.raises(ModelNotLoadedError, match="non-finite"):
            predict_credibility("One two three four five six")


def _build_calibrated_pa_artifact(tmp_path: Path) -> Path:
    """Train a tiny TF-IDF + CalibratedClassifierCV(PassiveAggressiveClassifier) artifact."""
    texts = [
        "central bank announced benchmark interest rate unchanged quarterly inflation data",
        "parliament passed annual infrastructure budget bill after committee review",
        "ministry published official employment statistics report for third quarter",
        "shocking leaked secret global elite hiding miracle cure doctors hate",
        "unbelievable breaking scandal video deleted mainstream media before election",
        "secret conspiracy exposed urgent share before internet censorship deletes post",
    ]
    labels = [1, 1, 1, 0, 0, 0]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        classifier = CalibratedClassifierCV(
            PassiveAggressiveClassifier(random_state=42),
            cv=2,
            method="sigmoid",
        )
        pipeline = Pipeline([("tfidf", vectorizer), ("clf", classifier)])
        pipeline.fit(texts, labels)

    artifact = {
        "pipeline": pipeline,
        "vectorizer": pipeline.named_steps["tfidf"],
        "classifier": pipeline.named_steps["clf"],
        "classes": {0: "FAKE", 1: "REAL"},
        "metadata": {"metrics": {"f1": 1.0}},
    }

    model_path = tmp_path / "pa_model.pkl"
    joblib.dump(artifact, model_path)
    return model_path


def test_highlights_are_sorted_normalized_and_verdict_aligned(tmp_path: Path) -> None:
    model_path = _build_calibrated_pa_artifact(tmp_path)
    fake_article = (
        "SHOCKING leaked secret! Global elites hiding miracle cure before "
        "mainstream media deletes this breaking scandal video."
    )
    real_article = (
        "Parliament passed the annual infrastructure budget bill after committee review "
        "and central bank officials published quarterly inflation statistics."
    )

    with (
        patch("backend.predictor.MODEL_PATH", model_path),
        patch("backend.predictor.warmup"),
        patch("backend.predictor.preprocess_text", side_effect=lambda s: " ".join(s.lower().split())),
    ):
        fake_res = predict_credibility(fake_article, top_k=5)
        real_res = predict_credibility(real_article, top_k=5)

    for res, expected_verdict in ((fake_res, "FAKE"), (real_res, "REAL")):
        assert res["verdict"] == expected_verdict
        highlights = res["highlights"]
        assert isinstance(highlights, list)
        assert 1 <= len(highlights) <= 5

        weights = [item["weight"] for item in highlights]
        assert weights[0] == 1.0
        assert weights == sorted(weights, reverse=True)
        assert all(isinstance(w, float) and math.isfinite(w) and 0.0 < w <= 1.0 for w in weights)

    fake_words = {item["word"] for item in fake_res["highlights"]}
    real_words = {item["word"] for item in real_res["highlights"]}
    assert fake_words.isdisjoint(real_words)
    assert any(any(t in w for t in ("shocking", "leaked", "secret", "miracle", "scandal")) for w in fake_words)
    assert any(any(t in w for t in ("parliament", "budget", "central", "bank", "committee", "inflation")) for w in real_words)


def test_highlights_map_lemmatized_tokens_back_to_surface_words(tmp_path: Path) -> None:
    texts = [
        "researcher study quarterly inflation statistic central bank report",
        "ministry publish official annual budget review parliament",
        "economist analyze national employment data committee report",
        "shock miracle cure secret doctor hate mainstream medium",
        "break scandal video delete conspiracy expose urgent share",
        "secret elite hide miracle cure internet censorship delete",
    ]
    labels = [1, 1, 1, 0, 0, 0]

    pipeline = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2))), ("clf", LogisticRegression(random_state=42))])
    pipeline.fit(texts, labels)
    artifact = {
        "pipeline": pipeline,
        "vectorizer": pipeline.named_steps["tfidf"],
        "classifier": pipeline.named_steps["clf"],
        "classes": {0: "FAKE", 1: "REAL"},
    }
    model_path = tmp_path / "lemma_model.pkl"
    joblib.dump(artifact, model_path)

    # Raw text uses inflected forms ("Researchers", "studied", "statistics", "reports")
    raw_article = (
        "Researchers studied quarterly inflation statistics and published official "
        "central bank reports for Parliament."
    )

    with patch("backend.predictor.MODEL_PATH", model_path):
        res = predict_credibility(raw_article, top_k=8)

    assert res["verdict"] == "REAL"
    highlighted_words = [item["word"] for item in res["highlights"]]
    assert len(highlighted_words) > 0
    lower_raw = raw_article.lower()
    for word in highlighted_words:
        assert word.lower() in lower_raw, f"Expected '{word}' to appear in raw article text"


def test_predict_credibility_with_trained_model_artifact() -> None:
    real_model_path = Path(__file__).resolve().parent.parent / "models" / "model.pkl"
    if not real_model_path.is_file():
        pytest.skip(f"Trained model artifact not found at {real_model_path}")

    sample_article = (
        "The Federal Reserve held its benchmark interest rate steady on Wednesday, "
        "citing moderating inflation figures and steady labor market growth across "
        "major regional sectors during the third quarter."
    )

    # Warm up once, then measure inference + explainability latency
    _ = predict_credibility(sample_article)
    start = time.perf_counter()
    res = predict_credibility(sample_article)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert res["verdict"] in ("REAL", "FAKE")
    assert len(res["highlights"]) > 0
    assert elapsed_ms < 100.0, f"Expected < 100ms with explainability, took {elapsed_ms:.2f}ms"
