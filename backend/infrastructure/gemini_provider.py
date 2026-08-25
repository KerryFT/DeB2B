from __future__ import annotations

import asyncio
import json
from typing import Any

from google import genai
from google.genai import types

from backend.application.ports import LLMResult


class GeminiLLMProvider:
    """Google Gemini implementation of the provider-neutral LLM port."""

    name = "gemini"

    def __init__(self, *, api_key: str, timeout_seconds: float) -> None:
        self.client = genai.Client(api_key=api_key)
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _usage(response: object) -> tuple[int | None, int | None]:
        usage = getattr(response, "usage_metadata", None)
        return (
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
        )

    async def generate_structured(
        self, *, task: str, prompt: str, schema: dict[str, Any], model: str
    ) -> LLMResult:
        started = asyncio.get_running_loop().time()
        thinking_level = (
            types.ThinkingLevel.MEDIUM
            if task == "case_analysis"
            else types.ThinkingLevel.LOW
        )
        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=schema,
                        temperature=0.1,
                        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                    ),
                ),
                timeout=self.timeout_seconds,
            )
            text = response.text or ""
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("structured response must be a JSON object")
            input_tokens, output_tokens = self._usage(response)
            return LLMResult(
                self.name,
                model,
                data,
                None,
                round((asyncio.get_running_loop().time() - started) * 1000),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                schema_valid=True,
            )
        except Exception as exc:  # provider/network/schema errors are a fail-closed boundary
            return LLMResult(
                self.name,
                model,
                None,
                None,
                round((asyncio.get_running_loop().time() - started) * 1000),
                error_class=type(exc).__name__,
            )

    async def generate_text(self, *, task: str, prompt: str, model: str) -> LLMResult:
        started = asyncio.get_running_loop().time()
        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        thinking_config=types.ThinkingConfig(
                            thinking_level=(
                                types.ThinkingLevel.MEDIUM
                                if task == "case_analysis"
                                else types.ThinkingLevel.LOW
                            )
                        ),
                    ),
                ),
                timeout=self.timeout_seconds,
            )
            input_tokens, output_tokens = self._usage(response)
            return LLMResult(
                self.name,
                model,
                None,
                response.text or "",
                round((asyncio.get_running_loop().time() - started) * 1000),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                schema_valid=True,
            )
        except Exception as exc:
            return LLMResult(
                self.name,
                model,
                None,
                None,
                round((asyncio.get_running_loop().time() - started) * 1000),
                error_class=type(exc).__name__,
            )
