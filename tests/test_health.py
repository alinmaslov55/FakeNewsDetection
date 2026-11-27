from fastapi.testclient import TestClient

import backend.app as app_module
from backend.predictor import ModelNotLoadedError

client = TestClient(app_module.app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Fake News Detection API is running"}


def test_health_model_loaded(monkeypatch):
    monkeypatch.setattr(app_module, "load_model", lambda: {"pipeline": object()})
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "version": "0.1.0",
        "model_loaded": True,
    }


def test_health_model_not_loaded(monkeypatch):
    def _raise_missing():
        raise ModelNotLoadedError("Model missing")

    monkeypatch.setattr(app_module, "load_model", _raise_missing)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "version": "0.1.0",
        "model_loaded": False,
    }
