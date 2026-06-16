"""
Qwen / DashScope LLM provider — text, vision, and video-frame QC.

Supports both text-only and multimodal (image/video-frame) calls via
the DashScope REST API.
"""
import base64
import json
import os
from pathlib import Path

import httpx

from src.llm.provider_base import (
    LLMImageCompareResult,
    LLMJsonResult,
    LLMTextResult,
    LLMVideoCompareResult,
    MultimodalLLMProviderBase,
)
from src.llm.provider_config import (
    DEFAULT_QWEN_TEXT_MODEL,
    DEFAULT_QWEN_VISION_MODEL,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
    QWEN_TEXT_ENDPOINT,
    QWEN_VISION_ENDPOINT,
)


def _encode_image(path_or_url: str) -> dict:
    """Return a DashScope-compatible image content block."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return {"image": path_or_url}
    p = Path(path_or_url)
    if p.exists():
        data = base64.b64encode(p.read_bytes()).decode()
        suffix = p.suffix.lstrip(".").lower() or "jpeg"
        mime = f"image/{suffix}"
        return {"image": f"data:{mime};base64,{data}"}
    return {"image": path_or_url}


def _post_sync(url: str, headers: dict, payload: dict, timeout: int, retries: int) -> dict:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                import time
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Qwen API call failed after {retries + 1} attempts: {last_exc}") from last_exc


class QwenProvider(MultimodalLLMProviderBase):
    provider_name = "qwen"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY", "")
        self.text_model = os.environ.get("QWEN_TEXT_MODEL", DEFAULT_QWEN_TEXT_MODEL)
        self.vision_model = os.environ.get("QWEN_VISION_MODEL", DEFAULT_QWEN_VISION_MODEL)
        self._timeout = LLM_TIMEOUT_SECONDS
        self._retries = LLM_MAX_RETRIES

    @property
    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def complete_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMTextResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.text_model,
            "input": {"messages": messages},
            "parameters": {"result_format": "message"},
        }
        raw = _post_sync(QWEN_TEXT_ENDPOINT, self._auth_headers, payload, self._timeout, self._retries)
        text = raw.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        return LLMTextResult(
            text=text,
            provider_name=self.provider_name,
            model_name=self.text_model,
            usage=usage,
            raw_response=raw,
        )

    def extract_json(
        self,
        prompt: str,
        schema_hint: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMJsonResult:
        sys = system_prompt or "You are a JSON extraction assistant. Reply ONLY with valid JSON, no markdown fences."
        if schema_hint:
            sys = f"{sys}\n\nExpected JSON schema:\n{schema_hint}"
        result = self.complete_text(prompt, system_prompt=sys)
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            data = json.loads(text)
        except Exception:
            data = {"_error": "JSON parse failed", "_raw": result.text}
        return LLMJsonResult(
            data=data,
            provider_name=self.provider_name,
            model_name=self.text_model,
            raw_text=result.text,
            usage=result.usage,
        )

    def compare_images(
        self,
        images: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMImageCompareResult:
        content: list[dict] = []
        for img in images:
            content.append(_encode_image(img))
        content.append({"text": question})

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": [{"text": system_prompt}]})
        messages.append({"role": "user", "content": content})

        payload = {
            "model": self.vision_model,
            "input": {"messages": messages},
        }
        raw = _post_sync(QWEN_VISION_ENDPOINT, self._auth_headers, payload, self._timeout, self._retries)

        choices = raw.get("output", {}).get("choices", [{}])
        raw_text = ""
        if choices:
            msg_content = choices[0].get("message", {}).get("content", "")
            if isinstance(msg_content, list):
                for block in msg_content:
                    if isinstance(block, dict) and "text" in block:
                        raw_text += block["text"]
            else:
                raw_text = str(msg_content)

        stripped = raw_text.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("```")[1]
            if stripped.startswith("json"):
                stripped = stripped[4:]
        try:
            result_json = json.loads(stripped)
        except Exception:
            result_json = {"_error": "JSON parse failed", "_raw": raw_text}

        return LLMImageCompareResult(
            result_json=result_json,
            provider_name=self.provider_name,
            model_name=self.vision_model,
            raw_text=raw_text,
            usage=raw.get("usage", {}),
        )

    def compare_video_frames(
        self,
        frames: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMVideoCompareResult:
        result = self.compare_images(frames, question, system_prompt=system_prompt, **kwargs)
        return LLMVideoCompareResult(
            result_json=result.result_json,
            provider_name=self.provider_name,
            model_name=self.vision_model,
            frames_used=len(frames),
            raw_text=result.raw_text,
            usage=result.usage,
        )
