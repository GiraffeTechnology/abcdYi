import os
import json
import httpx
from src.llm.provider import LLMProvider


class QwenProvider(LLMProvider):
    provider_name = "qwen"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("QWEN_API_KEY", "")
        self.model = os.environ.get("QWEN_MODEL", "qwen-plus")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    async def complete(self, prompt: str, system: str = "") -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "input": {
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ]
                    },
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["output"]["text"]

    async def extract_json(self, prompt: str, system: str = "") -> dict:
        text = await self.complete(prompt, system)
        try:
            return json.loads(text)
        except Exception:
            return {"_error": "JSON parse failed", "_raw": text}
