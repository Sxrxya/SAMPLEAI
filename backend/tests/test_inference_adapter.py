import json
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.schemas import ResumeExtractionPayload
from app.services.inference import HostedInferenceClient


class FakeHuggingFaceClient:
    def __init__(self) -> None:
        self.chat_request = None
        self.embedding_request = None

    async def chat_completion(self, **kwargs):
        self.chat_request = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "schema_version": "resume.v1",
                                "skills": [],
                                "work_history": [],
                                "education": [],
                                "projects": [],
                                "certifications": [],
                                "languages": [],
                                "unknown_fields": [],
                            }
                        )
                    )
                )
            ],
            model="test-chat-model",
        )

    async def feature_extraction(self, text, *, model):
        self.embedding_request = (text, model)
        return [[3.0, 4.0]]

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_huggingface_chat_and_embedding_adapter(monkeypatch):
    settings = Settings(
        inference_enabled=True,
        inference_provider="auto",
        inference_api_key=SecretStr("test-token"),
        inference_chat_model="test-chat-model",
        inference_embedding_model="test-embedding-model",
    )
    client = HostedInferenceClient(settings)
    fake = FakeHuggingFaceClient()
    monkeypatch.setattr(client, "_client", lambda: fake)

    extraction, model_id = await client.extract_resume("Sample resume text")
    vector, embedding_model = await client.embed("Resume query")

    assert isinstance(extraction, ResumeExtractionPayload)
    assert model_id == "test-chat-model"
    assert fake.chat_request["model"] == "test-chat-model"
    assert fake.chat_request["response_format"]["type"] == "json"
    assert fake.embedding_request == ("Resume query", "test-embedding-model")
    assert vector == pytest.approx([0.6, 0.8])
    assert embedding_model == "test-embedding-model"