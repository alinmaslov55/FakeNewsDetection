"""FastAPI application entrypoint for the Fake News Detection API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.predictor import ModelNotLoadedError, load_model, predict_credibility
from backend.schemas import HealthResponse, PredictionRequest, PredictionResponse
from backend.scraper import (
    EmptyArticleError,
    InvalidURLError,
    ScrapeFetchError,
    extract_article_text,
)

API_VERSION = "0.1.0"

app = FastAPI(
    title="Fake News Detection API",
    description="Backend API for Fake News Detection using NLP and Machine Learning",
    version=API_VERSION,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint - verification / hello world."""
    return {"message": "Fake News Detection API is running"}


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint reporting service status and ML model readiness."""
    try:
        load_model()
        model_loaded = True
    except ModelNotLoadedError:
        model_loaded = False

    return HealthResponse(
        status="healthy",
        version=API_VERSION,
        model_loaded=model_loaded,
    )


@app.post(
    "/api/predict",
    response_model=PredictionResponse,
    responses={
        400: {"description": "Disallowed URL, insufficient article content, or too few meaningful tokens."},
        502: {"description": "Upstream news site unreachable, timed out, or blocked scraping."},
        503: {"description": "Trained ML model artifact is missing or failed to load."},
    },
)
def predict_news(payload: PredictionRequest) -> PredictionResponse:
    """Analyze news article credibility from raw text or a public article URL."""
    title: str | None = None

    if payload.url is not None:
        try:
            scraped = extract_article_text(str(payload.url))
        except (InvalidURLError, EmptyArticleError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except ScrapeFetchError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        title = scraped.get("title") or None
        body_text = scraped["text"]
        analysis_text = f"{title}\n\n{body_text}" if title else body_text
        returned_text = body_text
    else:
        assert payload.text is not None  # Guaranteed by PredictionRequest validator
        analysis_text = payload.text
        returned_text = payload.text

    try:
        prediction = predict_credibility(analysis_text)
    except ModelNotLoadedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return PredictionResponse(
        verdict=prediction["verdict"],
        confidence=prediction["confidence"],
        title=title,
        text=returned_text,
        highlights=prediction.get("highlights", []),
    )
