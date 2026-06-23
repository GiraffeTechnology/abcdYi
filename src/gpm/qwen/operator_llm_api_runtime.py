from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig

_QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_QWEN_DEFAULT_MODEL = "qwen-turbo"
_OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


@runtime_checkable
class LLMApiProvider(Protocol):
    """Provider-agnostic protocol for LLM API backends."""

    provider_name: str

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]: ...


class _QwenProvider:
    """Qwen/DashScope-compatible provider via httpx. No vendor SDK required."""

    provider_name = "qwen"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        self._api_key = config.qwen_api_key
        self._base_url = (config.qwen_api_base_url or _QWEN_DEFAULT_BASE_URL).rstrip("/")
        self._model = config.qwen_api_model or _QWEN_DEFAULT_MODEL
        self._timeout = config.api_timeout_seconds

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        url = f"{self._base_url}/chat/completions"

        response = httpx.post(url, json=payload, headers=headers, timeout=self._timeout)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


class _OpenAICompatibleProvider:
    """OpenAI-compatible chat completions provider via httpx. Configurable base URL."""

    provider_name = "openai_compatible"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        self._api_key = config.qwen_api_key
        self._base_url = (config.qwen_api_base_url or _OPENAI_DEFAULT_BASE_URL).rstrip("/")
        self._model = config.qwen_api_model or "gpt-3.5-turbo"
        self._timeout = config.api_timeout_seconds

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        url = f"{self._base_url}/chat/completions"

        response = httpx.post(url, json=payload, headers=headers, timeout=self._timeout)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


class _CustomHttpProvider:
    """Generic JSON POST provider via httpx. Operator supplies the full base URL."""

    provider_name = "custom_http"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        if not config.qwen_api_base_url:
            raise RuntimeError(
                "custom_http provider requires QWEN_API_BASE_URL to be set."
            )
        self._api_key = config.qwen_api_key
        self._base_url = config.qwen_api_base_url.rstrip("/")
        self._model = config.qwen_api_model or ""
        self._timeout = config.api_timeout_seconds

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        import httpx

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {"prompt": prompt, "schema_name": schema_name}
        if self._model:
            payload["model"] = self._model

        response = httpx.post(self._base_url, json=payload, headers=headers, timeout=self._timeout)
        response.raise_for_status()
        return response.json()


_PROVIDERS: dict[str, type] = {
    "qwen": _QwenProvider,
    "openai_compatible": _OpenAICompatibleProvider,
    "custom_http": _CustomHttpProvider,
}


class OperatorLLMApiRuntime:
    """Operator-selected LLM API runtime. Default off; never selected automatically.

    Requires explicit operator configuration:
      GPM_ENABLE_QWEN_LLM_API=true
      GPM_QWEN_RUNTIME_MODE=llm_api
      QWEN_API_KEY or DASHSCOPE_API_KEY

    Token is never printed or persisted.
    """

    runtime_mode = "llm_api"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        if not config.enable_llm_api:
            raise RuntimeError(
                "Qwen LLM API mode is disabled. "
                "Set GPM_ENABLE_QWEN_LLM_API=true to enable operator-selected LLM API mode."
            )
        if not config.qwen_api_key:
            raise RuntimeError(
                "Qwen LLM API mode requires QWEN_API_KEY or DASHSCOPE_API_KEY to be set. "
                "Provide an operator token to use this runtime."
            )

        provider_cls = _PROVIDERS.get(config.llm_provider)
        if provider_cls is None:
            raise RuntimeError(
                f"Unknown LLM provider: {config.llm_provider!r}. "
                f"Supported providers: {sorted(_PROVIDERS)}"
            )

        self._provider: LLMApiProvider = provider_cls(config)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        return self._provider.generate_json(prompt, schema_name)
