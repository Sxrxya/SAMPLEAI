import asyncio
import json
import math
import re

from huggingface_hub import AsyncInferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

from app.core.config import Settings, get_settings
from app.schemas import JobExtractionPayload, ResumeExtractionPayload


class InferenceUnavailable(RuntimeError):
    pass


class InferenceProviderError(RuntimeError):
    pass


def _parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


class HostedInferenceClient:
    """Hugging Face hosted inference adapter; no local model fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._semaphore: asyncio.Semaphore | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.settings.inference_max_concurrency)
        return self._semaphore

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
            async with self._get_semaphore():
                try:
                    response = await client.chat_completion(
                        model=self.settings.inference_chat_model,
                        messages=[
                            {"role": "system", "content": f"{system_prompt}\nOutput MUST be valid raw JSON."},
                            {"role": "user", "content": source_text},
                        ],
                        temperature=0,
                        max_tokens=3000,
                        response_format={"type": "json", "value": schema},
                    )
                except Exception:
                    response = await client.chat_completion(
                        model=self.settings.inference_chat_model,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    f"{system_prompt}\nReturn ONLY a valid JSON object matching "
                                    f"this schema: {json.dumps(schema)}"
                                ),
                            },
                            {"role": "user", "content": source_text},
                        ],
                        temperature=0,
                        max_tokens=3000,
                    )
            raw = response.choices[0].message.content
            if not isinstance(raw, str):
                raise ValueError("provider returned no JSON content")
            return _parse_json(raw), str(
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
            raise InferenceProviderError(f"Hugging Face chat request failed: {exc}") from exc
        finally:
            await client.close()

    async def extract_resume(self, source_text: str) -> tuple[ResumeExtractionPayload, str]:
        prompt = (
            "You are an expert AI resume extraction system. Extract structured factual information from the resume.\n"
            "CRITICAL EXTRACTION RULES:\n"
            "1. Extract ONLY facts explicitly supported by the resume content. NEVER fabricate employers, titles, skills, or dates.\n"
            "2. For skills and projects, classify evidence_level: 'DEMONSTRATED' (direct implementation evidence), 'CONTEXTUAL' (used in task/role), or 'CLAIMED' (merely listed).\n"
            "3. Explicitly report missing information in unknown_fields or field_statuses: 'EXTRACTED', 'NOT_FOUND', or 'NEEDS_REVIEW'.\n"
            "4. Include exact source text snippets in the evidence list for each item.\n"
            f"Return JSON conforming to schema: {json.dumps(ResumeExtractionPayload.model_json_schema())}"
        )
        payload, model_id = await self._chat_json(
            prompt, source_text, ResumeExtractionPayload.model_json_schema()
        )
        return ResumeExtractionPayload.model_validate(payload), model_id

    async def extract_job(self, source_text: str) -> tuple[JobExtractionPayload, str]:
        prompt = (
            "You are an expert job description analysis system. Extract requirements strictly from the text.\n"
            "CRITICAL EXTRACTION RULES:\n"
            "1. Separate required_skills from preferred_skills; never promote preferred skills to required.\n"
            "2. Extract min_experience_months (e.g. 3 years = 36 months) and max_experience_months if mentioned.\n"
            "3. Extract education requirements and certification requirements separately.\n"
            "4. Include exact evidence quotes from the JD for each requirement.\n"
            f"Return JSON conforming to schema: {json.dumps(JobExtractionPayload.model_json_schema())}"
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
        async with self._get_semaphore():
            try:
                truncated_text = text[:2000].strip() or "empty"
                output = await client.feature_extraction(
                    truncated_text,
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
                raise InferenceProviderError(f"Hugging Face embedding request failed: {exc}") from exc
            finally:
                await client.close()
