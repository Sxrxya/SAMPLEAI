import asyncio
import json
import math

from huggingface_hub import AsyncInferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

from app.core.config import Settings, get_settings
from app.schemas import JobExtractionPayload, ResumeExtractionPayload


class InferenceUnavailable(RuntimeError):
    pass


class InferenceProviderError(RuntimeError):
    pass


class HostedInferenceClient:
    """Hugging Face hosted inference adapter; no local model fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._semaphore = asyncio.Semaphore(self.settings.inference_max_concurrency)

    def _ensure_configured(self) -> None:
        self.settings.validate_inference()
        if not self.settings.inference_enabled:
            raise InferenceUnavailable("Hosted inference is disabled")

    def _client(self) -> AsyncInferenceClient:
        return AsyncInferenceClient(
            provider=self.settings.inference_provider,
            token=self.settings.inference_api_key.get_secret_value(),
            timeout=self.settings.inference_timeout_seconds,
        )

    async def _chat_json(
        self, system_prompt: str, source_text: str, schema: dict
    ) -> tuple[dict, str]:
        self._ensure_configured()
        client = self._client()
        try:
            async with self._semaphore:
                response = await client.chat_completion(
                    model=self.settings.inference_chat_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": source_text},
                    ],
                    temperature=0,
                    max_tokens=3000,
                    response_format={"type": "json", "value": schema},
                )
            raw = response.choices[0].message.content
            if not isinstance(raw, str):
                raise ValueError("provider returned no JSON content")
            return json.loads(raw), str(
                response.model or self.settings.inference_chat_model
            )
        except (
            HfHubHTTPError,
            InferenceTimeoutError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise InferenceProviderError("Hugging Face chat request failed") from exc
        finally:
            await client.close()

    async def extract_resume(self, source_text: str) -> tuple[ResumeExtractionPayload, str]:
        prompt = (
            "Extract only supported facts from the resume. Never infer missing facts. "
            "Return JSON matching this schema: "
            f"{ResumeExtractionPayload.model_json_schema()}. Include source evidence and "
            "page numbers "
            "when available. Put absent requested information in unknown_fields."
        )
        payload, model_id = await self._chat_json(
            prompt, source_text, ResumeExtractionPayload.model_json_schema()
        )
        return ResumeExtractionPayload.model_validate(payload), model_id

    async def extract_job(self, source_text: str) -> tuple[JobExtractionPayload, str]:
        prompt = (
            "Extract requirements only from the provided job description. Separate required and "
            "preferred qualifications; do not invent criteria. Return JSON matching this schema: "
            f"{JobExtractionPayload.model_json_schema()}. Include evidence for each requirement."
        )
        payload, model_id = await self._chat_json(
            prompt, source_text, JobExtractionPayload.model_json_schema()
        )
        return JobExtractionPayload.model_validate(payload), model_id

    async def embed(self, text: str) -> tuple[list[float], str]:
        self._ensure_configured()
        if not self.settings.inference_embedding_model:
            raise InferenceUnavailable("Embedding model is not configured")
        client = self._client()
        async with self._semaphore:
            try:
                output = await client.feature_extraction(
                    text,
                    model=self.settings.inference_embedding_model,
                )
                vector = output.tolist() if hasattr(output, "tolist") else output
                while vector and isinstance(vector[0], list):
                    vector = vector[-1] if len(vector) > 1 else vector[0]
                normalized = [float(value) for value in vector]
                magnitude = math.sqrt(sum(value * value for value in normalized))
                if not magnitude:
                    raise ValueError("provider returned an empty embedding")
                return [value / magnitude for value in normalized], (
                    self.settings.inference_embedding_model
                )
            except (
                HfHubHTTPError,
                InferenceTimeoutError,
                IndexError,
                TypeError,
                ValueError,
            ) as exc:
                raise InferenceProviderError("Hugging Face embedding request failed") from exc
            finally:
                await client.close()
