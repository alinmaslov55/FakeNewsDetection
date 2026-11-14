"""Verification tests for the trained MLP-01 model artifact (models/model.pkl)."""

from __future__ import annotations

from pathlib import Path
import joblib
import numpy as np
import pytest

from backend.preprocessing import preprocess_text

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "model.pkl"


@pytest.fixture(scope="module")
def artifact() -> dict:
    if not MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def test_artifact_structure_and_metadata(artifact: dict):
    for key in ("pipeline", "vectorizer", "classifier", "classes", "metadata"):
        assert key in artifact, f"Missing expected key '{key}' in model artifact"

    assert artifact["classes"] == {0: "FAKE", 1: "REAL"}
    metrics = artifact["metadata"]["metrics"]
    assert metrics["f1"] >= 0.90, f"Expected test F1 >= 0.90, got {metrics['f1']}"


def test_artifact_predict_proba_and_linear_weights(artifact: dict):
    pipeline = artifact["pipeline"]
    vectorizer = artifact["vectorizer"]
    classifier = artifact["classifier"]

    sample_real = preprocess_text(
        "The central bank announced Thursday that benchmark interest rates remain unchanged "
        "following moderate quarterly inflation data released by the statistics bureau."
    )
    sample_fake = preprocess_text(
        "SHOCKING LEAKED SECRET: Global elites are hiding this miracle cure that doctors "
        "hate before the mainstream media deletes this video forever!"
    )

    probs = pipeline.predict_proba([sample_real, sample_fake])
    assert probs.shape == (2, 2)
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
    assert np.allclose(probs.sum(axis=1), 1.0)

    # Verify linear feature weights exist and align with TF-IDF vocabulary
    if hasattr(classifier, "coef_"):
        coef = classifier.coef_
    elif hasattr(classifier, "calibrated_classifiers_"):
        coef = np.mean(
            [c.estimator.coef_ for c in classifier.calibrated_classifiers_],
            axis=0,
        )
    else:
        pytest.fail("Classifier exposes neither 'coef_' nor 'calibrated_classifiers_'")

    vocab_size = len(vectorizer.get_feature_names_out())
    assert coef.shape[1] == vocab_size
    assert np.all(np.isfinite(coef))
