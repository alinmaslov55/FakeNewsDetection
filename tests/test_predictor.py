"""Unit tests for model loading, credibility inference, and confidence scoring (MLP-02)."""

from __future__ import annotations

from pathlib import Path
import time
from unittest.mock import Mock, patch

import joblib
import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
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
