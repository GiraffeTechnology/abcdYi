from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
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
        self._api_key = config.llm_api_key
        self._base_url = (config.llm_api_base_url or _QWEN_DEFAULT_BASE_URL).rstrip("/")
        self._model = config.llm_api_model or _QWEN_DEFAULT_MODEL
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

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GPMRuntimeUnavailableError(
                reason=f"LLM API returned HTTP {exc.response.status_code}",
                attempted_runtime="llm_api",
                safe_message=(
                    f"LLM API request failed with HTTP {exc.response.status_code}. "
                    "Check GPM_LLM_API_KEY and API endpoint availability."
                ),
            ) from exc
        except httpx.RequestError as exc:
            raise GPMRuntimeUnavailableError(
                reason=f"LLM API network error: {type(exc).__name__}",
                attempted_runtime="llm_api",
                safe_message=(
                    "LLM API request failed due to a network error. "
                    "Check connectivity and API endpoint configuration."
                ),
            ) from exc

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


class _OpenAICompatibleProvider:
    """OpenAI-compatible chat completions provider via httpx. Configurable base URL."""

    provider_name = "openai_compatible"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        self._api_key = config.llm_api_key
        self._base_url = (config.llm_api_base_url or _OPENAI_DEFAULT_BASE_URL).rstrip("/")
        self._model = config.llm_api_model or "gpt-3.5-turbo"
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

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GPMRuntimeUnavailableError(
                reason=f"LLM API returned HTTP {exc.response.status_code}",
                attempted_runtime="llm_api",
                safe_message=(
                    f"LLM API request failed with HTTP {exc.response.status_code}. "
                    "Check GPM_LLM_API_KEY and API endpoint availability."
                ),
            ) from exc
        except httpx.RequestError as exc:
            raise GPMRuntimeUnavailableError(
                reason=f"LLM API network error: {type(exc).__name__}",
                attempted_runtime="llm_api",
                safe_message=(
                    "LLM API request failed due to a network error. "
                    "Check connectivity and API endpoint configuration."
                ),
            ) from exc

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


class _CustomHttpProvider:
    """Generic JSON POST provider via httpx. Operator supplies the full base URL."""

    provider_name = "custom_http"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        if not config.llm_api_base_url:
            raise RuntimeError(
                "custom_http provider requires GPM_LLM_API_BASE_URL (or QWEN_API_BASE_URL) to be set."
            )
        self._api_key = config.llm_api_key
        self._base_url = config.llm_api_base_url.rstrip("/")
        self._model = config.llm_api_model or ""
        self._timeout = config.api_timeout_seconds

    def generate_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        import httpx

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {"prompt": prompt, "schema_name": schema_name}
        if self._model:
            payload["model"] = self._model

        try:
            response = httpx.post(self._base_url, json=payload, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GPMRuntimeUnavailableError(
                reason=f"LLM API returned HTTP {exc.response.status_code}",
                attempted_runtime="llm_api",
                safe_message=(
                    f"LLM API request failed with HTTP {exc.response.status_code}. "
                    "Check GPM_LLM_API_KEY and API endpoint availability."
                ),
            ) from exc
        except httpx.RequestError as exc:
            raise GPMRuntimeUnavailableError(
                reason=f"LLM API network error: {type(exc).__name__}",
                attempted_runtime="llm_api",
                safe_message=(
                    "LLM API request failed due to a network error. "
                    "Check connectivity and API endpoint configuration."
                ),
            ) from exc
        return response.json()


_PROVIDERS: dict[str, type] = {
    "qwen": _QwenProvider,
    "openai_compatible": _OpenAICompatibleProvider,
    "custom_http": _CustomHttpProvider,
}


class OperatorLLMApiRuntime:
    """Operator-selected LLM API runtime. Default off; never selected automatically.

    Requires explicit operator configuration:
      GPM_ENABLE_LLM_API=true       (canonical; GPM_ENABLE_QWEN_LLM_API is alias)
      GPM_LLM_RUNTIME_MODE=llm_api  (canonical; GPM_QWEN_RUNTIME_MODE is alias)
      GPM_LLM_API_KEY=<token>       (canonical; QWEN_API_KEY / DASHSCOPE_API_KEY are aliases)

    Token is never printed or persisted.
    """

    runtime_mode = "llm_api"

    def __init__(self, config: QwenRuntimeConfig) -> None:
        if not config.enable_llm_api:
            raise RuntimeError(
                "LLM API mode is disabled. "
                "Set GPM_ENABLE_LLM_API=true (or GPM_ENABLE_QWEN_LLM_API=true) "
                "to enable operator-selected LLM API mode."
            )
        if not config.llm_api_key:
            raise RuntimeError(
                "LLM API mode requires GPM_LLM_API_KEY "
                "(or Qwen aliases QWEN_API_KEY / DASHSCOPE_API_KEY) to be set. "
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
