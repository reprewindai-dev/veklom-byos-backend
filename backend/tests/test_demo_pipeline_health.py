import asyncio

from backend.apps.api.routers import pipelines


def test_demo_pipeline_health_exposes_model_canary_fields(monkeypatch):
    monkeypatch.setattr(pipelines.settings, "GROQ_API_KEY", "gsk_live_key")
    monkeypatch.setattr(pipelines.settings, "LLM_FALLBACK", "groq")
    monkeypatch.setattr(pipelines.settings, "OLLAMA_BASE_URL", "")
    monkeypatch.setattr(pipelines.settings, "OPENAI_API_KEY", "")

    response = asyncio.run(pipelines.demo_pipeline_health())

    assert response["status"] == "healthy"
    assert response["pipeline"] == "demo"
    assert response["llm_ok"] is True
    assert response["groq_fallback_enabled"] is True
    assert "groq" in response["providers_configured"]


def test_demo_pipeline_health_rejects_placeholder_provider_config(monkeypatch):
    monkeypatch.setattr(pipelines.settings, "GROQ_API_KEY", "your-groq-key")
    monkeypatch.setattr(pipelines.settings, "LLM_FALLBACK", "groq")
    monkeypatch.setattr(pipelines.settings, "OLLAMA_BASE_URL", "")
    monkeypatch.setattr(pipelines.settings, "OPENAI_API_KEY", "placeholder")

    response = asyncio.run(pipelines.demo_pipeline_health())

    assert response["llm_ok"] is False
    assert response["groq_fallback_enabled"] is False
    assert response["providers_configured"] == []
