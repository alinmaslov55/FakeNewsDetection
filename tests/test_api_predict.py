from fastapi.testclient import TestClient

import backend.app as app_module
from backend.predictor import ModelNotLoadedError
from backend.scraper import EmptyArticleError, InvalidURLError, ScrapeFetchError

client = TestClient(app_module.app)

SAMPLE_TEXT = (
    "Federal officials released an independent economic report on Tuesday "
    "detailing regional employment gains across manufacturing and healthcare."
)
SAMPLE_HIGHLIGHTS = [
    {"word": "officials", "weight": 1.0},
    {"word": "economic", "weight": 0.72},
]


def test_predict_text_success(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_predict(text: str):
        captured["text"] = text
        return {
            "verdict": "REAL",
            "confidence": 0.9125,
            "highlights": SAMPLE_HIGHLIGHTS,
        }

    monkeypatch.setattr(app_module, "predict_credibility", _fake_predict)

    response = client.post("/api/predict", json={"text": SAMPLE_TEXT})
    assert response.status_code == 200
    assert captured["text"] == SAMPLE_TEXT
    assert response.json() == {
        "verdict": "REAL",
        "confidence": 0.9125,
        "title": None,
        "text": SAMPLE_TEXT,
        "highlights": SAMPLE_HIGHLIGHTS,
    }


def test_predict_url_success(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_extract(url: str):
        captured["url"] = url
        return {
            "url": url,
            "title": "Breaking Economic Report",
            "text": SAMPLE_TEXT,
        }

    def _fake_predict(text: str):
        captured["analyzed_text"] = text
        return {
            "verdict": "FAKE",
            "confidence": 0.875,
            "highlights": [{"word": "Breaking", "weight": 1.0}],
        }

    monkeypatch.setattr(app_module, "extract_article_text", _fake_extract)
    monkeypatch.setattr(app_module, "predict_credibility", _fake_predict)

    response = client.post(
        "/api/predict", json={"url": "https://example.com/articles/economy"}
    )
    assert response.status_code == 200
    assert captured["url"] == "https://example.com/articles/economy"
    assert captured["analyzed_text"] == f"Breaking Economic Report\n\n{SAMPLE_TEXT}"
    assert response.json() == {
        "verdict": "FAKE",
        "confidence": 0.875,
        "title": "Breaking Economic Report",
        "text": SAMPLE_TEXT,
        "highlights": [{"word": "Breaking", "weight": 1.0}],
    }


def test_predict_url_takes_precedence_over_text(monkeypatch):
    called: list[str] = []

    def _fake_extract(url: str):
        called.append(f"scrape:{url}")
        return {
            "url": url,
            "title": "Scraped Headline",
            "text": SAMPLE_TEXT,
        }

    def _fake_predict(text: str):
        called.append("predict")
        return {"verdict": "REAL", "confidence": 0.88, "highlights": []}

    monkeypatch.setattr(app_module, "extract_article_text", _fake_extract)
    monkeypatch.setattr(app_module, "predict_credibility", _fake_predict)

    response = client.post(
        "/api/predict",
        json={
            "url": "https://example.com/story",
            "text": "Ignored fallback text that is definitely long enough to pass length check.",
        },
    )
    assert response.status_code == 200
    assert called == ["scrape:https://example.com/story", "predict"]
    assert response.json()["title"] == "Scraped Headline"
    assert response.json()["text"] == SAMPLE_TEXT


def test_predict_validation_errors():
    # Empty body
    assert client.post("/api/predict", json={}).status_code == 422
    # Whitespace only
    assert client.post("/api/predict", json={"text": "   ", "url": "   "}).status_code == 422
    # Text shorter than 30 characters
    assert client.post("/api/predict", json={"text": "Too short"}).status_code == 422
    # Text exceeding 100_000 characters
    assert client.post("/api/predict", json={"text": "a" * 100_001}).status_code == 422


def test_predict_maps_invalid_url_to_400(monkeypatch):
    def _raise_invalid(url: str):
        raise InvalidURLError("Blocked private IP address.")

    monkeypatch.setattr(app_module, "extract_article_text", _raise_invalid)

    response = client.post("/api/predict", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 400
    assert "Blocked private IP" in response.json()["detail"]


def test_predict_maps_empty_article_to_400(monkeypatch):
    def _raise_empty(url: str):
        raise EmptyArticleError("No readable article text found.")

    monkeypatch.setattr(app_module, "extract_article_text", _raise_empty)

    response = client.post("/api/predict", json={"url": "https://example.com/paywall"})
    assert response.status_code == 400
    assert "No readable article text" in response.json()["detail"]


def test_predict_maps_insufficient_tokens_to_400(monkeypatch):
    def _raise_value_error(text: str):
        raise ValueError("Input must contain at least 5 meaningful tokens.")

    monkeypatch.setattr(app_module, "predict_credibility", _raise_value_error)

    response = client.post("/api/predict", json={"text": "12345 67890 12345 67890 12345 67890"})
    assert response.status_code == 400
    assert "meaningful tokens" in response.json()["detail"]


def test_predict_maps_scrape_fetch_error_to_502(monkeypatch):
    def _raise_fetch_error(url: str):
        raise ScrapeFetchError("Upstream request timed out.")

    monkeypatch.setattr(app_module, "extract_article_text", _raise_fetch_error)

    response = client.post("/api/predict", json={"url": "https://example.com/timeout"})
    assert response.status_code == 502
    assert "timed out" in response.json()["detail"]


def test_predict_maps_model_not_loaded_to_503(monkeypatch):
    def _raise_model_error(text: str):
        raise ModelNotLoadedError("Trained model artifact not found.")

    monkeypatch.setattr(app_module, "predict_credibility", _raise_model_error)

    response = client.post("/api/predict", json={"text": SAMPLE_TEXT})
    assert response.status_code == 503
    assert "not found" in response.json()["detail"]


def test_openapi_documents_predict_endpoint():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    predict_spec = response.json()["paths"]["/api/predict"]["post"]
    assert "200" in predict_spec["responses"]
    assert "400" in predict_spec["responses"]
    assert "422" in predict_spec["responses"]
    assert "502" in predict_spec["responses"]
    assert "503" in predict_spec["responses"]
