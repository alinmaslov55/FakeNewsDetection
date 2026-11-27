"""Pydantic v2 request and response schemas for the Fake News Detection API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

MIN_TEXT_LENGTH = 30
MAX_TEXT_LENGTH = 100_000


class HighlightToken(BaseModel):
    """Single influential token/phrase and its normalized attribution weight."""

    word: str = Field(..., description="Token or phrase appearing in the analyzed article.")
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized importance weight in [0.0, 1.0].",
    )


class PredictionRequest(BaseModel):
    """Request payload for credibility analysis via raw article text or URL.

    If both ``url`` and ``text`` are supplied, ``url`` takes precedence and the
    endpoint scrapes and analyzes the target article URL.
    """

    text: str | None = Field(
        default=None,
        description=(
            f"Raw news article text ({MIN_TEXT_LENGTH}–{MAX_TEXT_LENGTH} characters "
            "when 'url' is not provided)."
        ),
    )
    url: HttpUrl | str | None = Field(
        default=None,
        description="Public http/https URL of a news article to scrape and analyze.",
    )

    @model_validator(mode="after")
    def validate_text_or_url(self) -> PredictionRequest:
        """Normalize inputs and ensure at least one valid target is provided."""
        if self.text is not None:
            stripped_text = self.text.strip()
            self.text = stripped_text if stripped_text else None

        if self.url is not None:
            stripped_url = str(self.url).strip()
            self.url = stripped_url if stripped_url else None

        if self.url is None and self.text is None:
            raise ValueError("Either 'text' or 'url' must be provided and non-empty.")

        if self.url is None and self.text is not None:
            if len(self.text) < MIN_TEXT_LENGTH:
                raise ValueError(
                    f"'text' must be at least {MIN_TEXT_LENGTH} characters long "
                    f"(received {len(self.text)})."
                )
            if len(self.text) > MAX_TEXT_LENGTH:
                raise ValueError(
                    f"'text' must not exceed {MAX_TEXT_LENGTH} characters "
                    f"(received {len(self.text)})."
                )

        return self


class PredictionResponse(BaseModel):
    """Credibility verdict, calibrated confidence score, and explainability highlights."""

    verdict: Literal["REAL", "FAKE"] = Field(
        ..., description="Predicted credibility classification."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated probability for the predicted verdict in [0.0, 1.0].",
    )
    title: str | None = Field(
        default=None,
        description="Extracted article headline when analyzed from a URL.",
    )
    text: str = Field(..., description="The article text that was analyzed.")
    highlights: list[HighlightToken] = Field(
        default_factory=list,
        description="Top influential words/phrases ranked by descending importance.",
    )


class HealthResponse(BaseModel):
    """Service health and ML model readiness status."""

    status: str = Field(..., description="Service health indicator (e.g., 'healthy').")
    version: str = Field(..., description="Current API version.")
    model_loaded: bool = Field(
        ..., description="True if the ML model artifact is loaded and ready for inference."
    )
