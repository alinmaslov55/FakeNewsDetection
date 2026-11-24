"""Model loading, credibility inference, and confidence scoring logic."""

from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from backend.preprocessing import preprocess_text, warmup

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "model.pkl"
MIN_MEANINGFUL_TOKENS = 5
REQUIRED_ARTIFACT_KEYS = ("pipeline", "vectorizer", "classifier", "classes")


class ModelNotLoadedError(RuntimeError):
    """Raised when the serialized ML model artifact is missing, invalid, or cannot be loaded."""


def _validate_artifact(artifact: object, model_path: Path) -> dict[str, Any]:
    """Verify the loaded joblib artifact matches the expected MLP-01 dictionary schema."""
    if not isinstance(artifact, dict):
        raise ModelNotLoadedError(
            f"Invalid model artifact format at '{model_path}': expected dict, got {type(artifact).__name__}."
        )

    missing_keys = [key for key in REQUIRED_ARTIFACT_KEYS if artifact.get(key) is None]
    if missing_keys:
        raise ModelNotLoadedError(
            f"Model artifact at '{model_path}' is missing required keys: {', '.join(missing_keys)}."
        )

    pipeline = artifact["pipeline"]
    if not hasattr(pipeline, "predict_proba"):
        raise ModelNotLoadedError(
            f"Model pipeline at '{model_path}' does not expose 'predict_proba()'."
        )

    return artifact


@lru_cache(maxsize=1)
def _load_cached_artifact(resolved_path: str) -> dict[str, Any]:
    """Load, validate, and warm up the ML model artifact once per process."""
    path = Path(resolved_path)
    if not path.is_file():
        raise ModelNotLoadedError(
            f"Trained model artifact not found at '{path}'. Run the MLP-01 training pipeline first."
        )

    try:
        artifact = joblib.load(path)
    except Exception as exc:
        raise ModelNotLoadedError(
            f"Failed to deserialize model artifact at '{path}': {exc}"
        ) from exc

    validated = _validate_artifact(artifact, path)

    try:
        warmup()
    except Exception as exc:
        raise ModelNotLoadedError(
            f"Failed to initialize NLP preprocessing resources: {exc}"
        ) from exc

    return validated


def load_model(model_path: Path | str | None = None) -> dict[str, Any]:
    """
    Return the cached model artifact dictionary, loading from disk on first call.

    Args:
        model_path: Optional override path to a serialized `.pkl` model artifact.

    Returns:
        dict: Validated artifact containing 'pipeline', 'vectorizer', 'classifier', and 'classes'.

    Raises:
        ModelNotLoadedError: If the model file is missing, corrupted, or invalid.
    """
    target_path = Path(model_path).resolve() if model_path is not None else MODEL_PATH.resolve()
    return _load_cached_artifact(str(target_path))


def clear_model_cache() -> None:
    """Clear the in-memory cached model artifact (primarily for testing)."""
    _load_cached_artifact.cache_clear()


def is_model_loaded(model_path: Path | str | None = None) -> bool:
    """Return True if the model artifact can be loaded and is ready for inference."""
    try:
        load_model(model_path)
        return True
    except ModelNotLoadedError:
        return False


def _validate_and_preprocess(text: str) -> str:
    """Validate raw article text and normalize it using the shared NLP-01 pipeline."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input article text must be a non-empty string.")

    cleaned_text = preprocess_text(text)
    tokens = cleaned_text.split()
    if len(tokens) < MIN_MEANINGFUL_TOKENS:
        raise ValueError(
            f"Input text has insufficient meaningful tokens after preprocessing "
            f"({len(tokens)} found; at least {MIN_MEANINGFUL_TOKENS} required)."
        )
    return cleaned_text


def _resolve_verdict(pipeline: Any, classes_map: dict[Any, str], pred_col: int) -> str:
    """Map predicted probability column index to normalized 'REAL' or 'FAKE' verdict."""
    pipeline_classes = getattr(pipeline, "classes_", None)
    raw_label = pipeline_classes[pred_col] if pipeline_classes is not None else pred_col

    if raw_label in classes_map:
        verdict = str(classes_map[raw_label]).strip().upper()
    elif str(raw_label) in classes_map:
        verdict = str(classes_map[str(raw_label)]).strip().upper()
    else:
        verdict = str(raw_label).strip().upper()

    if verdict not in ("REAL", "FAKE"):
        raise ModelNotLoadedError(
            f"Model returned unsupported class label '{verdict}' (expected 'REAL' or 'FAKE')."
        )
    return verdict


def predict_credibility(text: str) -> dict[str, object]:
    """
    Predict credibility ('REAL' vs 'FAKE') and calibrated confidence for raw article text.

    Args:
        text: Raw article text string.

    Returns:
        dict: Containing 'verdict' ('REAL' | 'FAKE'), 'confidence' (float in [0.0, 1.0]),
            and 'highlights' (populated by MLP-03).

    Raises:
        ModelNotLoadedError: If the trained model artifact cannot be loaded.
        ValueError: If input text is empty or yields fewer than MIN_MEANINGFUL_TOKENS tokens.
    """
    artifact = load_model()
    cleaned_text = _validate_and_preprocess(text)

    pipeline = artifact["pipeline"]
    classes_map = artifact["classes"]

    probs = np.asarray(pipeline.predict_proba([cleaned_text])[0], dtype=float)
    if probs.ndim != 1 or probs.size == 0:
        raise ModelNotLoadedError("Model predict_proba() returned an invalid probability vector.")

    pred_col = int(np.argmax(probs))
    verdict = _resolve_verdict(pipeline, classes_map, pred_col)

    raw_prob = float(probs[pred_col])
    if not math.isfinite(raw_prob):
        raise ModelNotLoadedError("Model predict_proba() returned a non-finite confidence score.")

    confidence = round(min(1.0, max(0.0, raw_prob)), 4)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "highlights": [],
    }
