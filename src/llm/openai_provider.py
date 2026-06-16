"""
OpenAI provider — optional fallback.
Requires OPENAI_API_KEY.
"""
import base64
import json
import time
from pathlib import Path

import httpx

from src.llm.provider_base import (
    MultimodalLLMProviderBase,
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)
from src.llm.provider_config import (
    DEFAULT_OPENAI_TEXT_MODEL, DEFAULT_OPENAI_VISION_MODEL,
    LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES, get_openai_api_key,
)

_OPENAI_BASE = "https://api.openai.com/v1"


def _encode_image_content(path_or_url: str) -> dict:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
    else:
        p = Path(path_or_url)
        data = base64.b64encode(p.read_bytes()).decode()
        suffix = p.suffix.lstrip(".").lower() or "jpeg"
        url = f"data:image/{suffix};base64,{data}"
    return {"type": "image_url", "image_url": {"url": url}}


class OpenAIProvider(MultimodalLLMProviderBase):
    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_openai_api_key() or ""
        self.text_model = DEFAULT_OPENAI_TEXT_MODEL
        self.vision_model = DEFAULT_OPENAI_VISION_MODEL
        self._timeout = LLM_TIMEOUT_SECONDS
        self._retries = LLM_MAX_RETRIES

    def _post(self, payload: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = httpx.post(f"{_OPENAI_BASE}/chat/completions", headers=headers, json=payload, timeout=self._timeout)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if 400 <= exc.response.status_code < 500:
                    raise RuntimeError(f"OpenAI API rejected the request: {exc.response.text}") from exc
                last_exc = exc
                if attempt < self._retries:
                    time.sleep(2 ** attempt)
            except Exception as exc:
                last_exc = exc
                if attempt < self._retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"OpenAI API call failed after {self._retries + 1} attempts: {last_exc}") from last_exc

    def complete_text(self, prompt: str, system_prompt: str | None = None, **kwargs) -> LLMTextResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        raw = self._post({"model": self.text_model, "messages": messages})
        text = raw["choices"][0]["message"]["content"]
        return LLMTextResult(text=text, provider_name=self.provider_name, model_name=self.text_model, usage=raw.get("usage", {}), raw_response=raw)

    def extract_json(self, prompt: str, schema_hint: str | None = None, system_prompt: str | None = None, **kwargs) -> LLMJsonResult:
        sys = system_prompt or "You are a JSON extraction assistant. Reply ONLY with valid JSON, no markdown fences."
        if schema_hint:
            sys = f"{sys}\n\nExpected JSON schema:\n{schema_hint}"
        messages = [{"role": "system", "content": sys}, {"role": "user", "content": prompt}]
        raw = self._post({"model": self.text_model, "messages": messages, "response_format": {"type": "json_object"}})
        text = raw["choices"][0]["message"]["content"]
        try:
            data = json.loads(text)
        except Exception:
            data = {"_error": "JSON parse failed", "_raw": text}
        return LLMJsonResult(data=data, provider_name=self.provider_name, model_name=self.text_model, raw_text=text, usage=raw.get("usage", {}))

    def compare_images(self, images: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMImageCompareResult:
        content = [_encode_image_content(img) for img in images]
        content.append({"type": "text", "text": question})
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        raw = self._post({"model": self.vision_model, "messages": messages, "response_format": {"type": "json_object"}})
        text = raw["choices"][0]["message"]["content"]
        try:
            result_json = json.loads(text)
        except Exception:
            result_json = {"_error": "JSON parse failed", "_raw": text}
        return LLMImageCompareResult(result_json=result_json, provider_name=self.provider_name, model_name=self.vision_model, raw_text=text, usage=raw.get("usage", {}))

    def compare_video_frames(self, frames: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMVideoCompareResult:
        result = self.compare_images(frames, question, system_prompt=system_prompt, **kwargs)
        return LLMVideoCompareResult(
            result_json=result.result_json,
            provider_name=self.provider_name,
            model_name=self.vision_model,
            frames_used=len(frames),
            raw_text=result.raw_text,
            usage=result.usage,
        )
