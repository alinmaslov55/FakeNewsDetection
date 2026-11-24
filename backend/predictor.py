"""Model loading, credibility inference, confidence scoring, and explainability logic."""

from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
import re
from typing import Any

import joblib
import numpy as np

from backend.preprocessing import preprocess_text, warmup

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "model.pkl"
MIN_MEANINGFUL_TOKENS = 5
DEFAULT_TOP_HIGHLIGHTS = 12
REQUIRED_ARTIFACT_KEYS = ("pipeline", "vectorizer", "classifier", "classes")
_RAW_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


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


def _extract_linear_weights(classifier: Any) -> np.ndarray | None:
    """Extract a 1D linear weight vector from a classifier or CalibratedClassifierCV."""
    if hasattr(classifier, "coef_"):
        coef = np.asarray(classifier.coef_, dtype=float)
        if coef.ndim == 2:
            return coef[0]
        if coef.ndim == 1:
            return coef
        return None

    calibrated = getattr(classifier, "calibrated_classifiers_", None)
    if not calibrated:
        return None

    fold_coefs: list[np.ndarray] = []
    for entry in calibrated:
        base_est = getattr(entry, "estimator", None)
        if base_est is not None and hasattr(base_est, "coef_"):
            coef = np.asarray(base_est.coef_, dtype=float)
            fold_coefs.append(coef[0] if coef.ndim == 2 else coef.ravel())

    if not fold_coefs:
        return None
    return np.mean(fold_coefs, axis=0)


def _get_explainability_arrays(artifact: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
    """Return cached (feature_names, weights) arrays if supported by the loaded artifact."""
    cached = artifact.get("_explain_cache")
    if cached is not None:
        return cached

    vectorizer = artifact.get("vectorizer")
    classifier = artifact.get("classifier")
    if vectorizer is None or classifier is None:
        return None
    if not hasattr(vectorizer, "transform") or not hasattr(vectorizer, "get_feature_names_out"):
        return None

    weights = _extract_linear_weights(classifier)
    if weights is None:
        return None

    feature_names = np.asarray(vectorizer.get_feature_names_out())
    if feature_names.shape[0] != weights.shape[0]:
        return None

    pair = (feature_names, weights)
    artifact["_explain_cache"] = pair
    return pair


def _build_surface_lookup(raw_text: str) -> dict[str, str]:
    """
    Map preprocessed unigram/bigram lemmas back to surface substrings in raw_text.

    Preserves exact surface forms (e.g. 'studies' instead of 'study') so WEB-03
    can highlight exact substrings in the original article body.
    """
    raw_words = _RAW_WORD_RE.findall(raw_text)
    if not raw_words:
        return {}

    surface_map: dict[str, str] = {}
    token_lemmas: list[str] = []

    for word in raw_words:
        lower_word = word.lower()
        lemma = preprocess_text(lower_word)
        token_lemmas.append(lemma)
        if not lemma or " " in lemma:
            continue
        if lemma not in surface_map or lower_word == lemma:
            surface_map[lemma] = lower_word

    for idx in range(len(raw_words) - 1):
        lemma_a = token_lemmas[idx]
        lemma_b = token_lemmas[idx + 1]
        if not lemma_a or not lemma_b or " " in lemma_a or " " in lemma_b:
            continue
        bigram_key = f"{lemma_a} {lemma_b}"
        bigram_surface = f"{raw_words[idx].lower()} {raw_words[idx + 1].lower()}"
        if bigram_key not in surface_map or bigram_surface == bigram_key:
            surface_map[bigram_key] = bigram_surface

    return surface_map


def _compute_highlights(
    artifact: dict[str, Any],
    raw_text: str,
    cleaned_text: str,
    pred_col: int,
    *,
    top_k: int = DEFAULT_TOP_HIGHLIGHTS,
) -> list[dict[str, float | str]]:
    """Compute top-K verdict-aligned feature highlights normalized to (0.0, 1.0]."""
    if top_k <= 0:
        return []

    arrays = _get_explainability_arrays(artifact)
    if arrays is None:
        return []

    feature_names, weights = arrays
    vectorizer = artifact["vectorizer"]
    tfidf_vec = vectorizer.transform([cleaned_text])
    nonzero_cols = tfidf_vec.nonzero()[1]
    if nonzero_cols.size == 0:
        return []

    # Binary linear models: positive coef_ pushes toward classes_[1], negative toward classes_[0]
    direction = 1.0 if pred_col == 1 else -1.0
    tfidf_vals = np.asarray(tfidf_vec[0, nonzero_cols].toarray(), dtype=float).ravel()
    raw_scores = tfidf_vals * weights[nonzero_cols] * direction

    candidates: list[tuple[str, float]] = []
    for col_idx, score in zip(nonzero_cols, raw_scores):
        score_f = float(score)
        if score_f > 0.0 and math.isfinite(score_f):
            candidates.append((str(feature_names[col_idx]), score_f))

    if not candidates:
        return []

    candidates.sort(key=lambda item: item[1], reverse=True)
    surface_map = _build_surface_lookup(raw_text)

    selected: list[tuple[str, float]] = []
    seen_terms: set[str] = set()
    for feature, score in candidates:
        surface_term = surface_map.get(feature, feature)
        dedup_key = surface_term.lower()
        if dedup_key in seen_terms:
            continue
        seen_terms.add(dedup_key)
        selected.append((surface_term, score))
        if len(selected) >= top_k:
            break

    max_score = selected[0][1]
    if max_score <= 0.0 or not math.isfinite(max_score):
        return []

    return [
        {"word": term, "weight": round(min(1.0, max(0.0, score / max_score)), 4)}
        for term, score in selected
    ]


def predict_credibility(
    text: str,
    *,
    top_k: int = DEFAULT_TOP_HIGHLIGHTS,
) -> dict[str, object]:
    """
    Predict credibility ('REAL' vs 'FAKE'), calibrated confidence, and top highlights.

    Args:
        text: Raw article text string.
        top_k: Maximum number of influential highlight tokens to return.

    Returns:
        dict: Containing 'verdict' ('REAL' | 'FAKE'), 'confidence' (float in [0.0, 1.0]),
            and 'highlights' (list of {'word': str, 'weight': float} sorted descending).

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
    highlights = _compute_highlights(artifact, text, cleaned_text, pred_col, top_k=top_k)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "highlights": highlights,
    }
