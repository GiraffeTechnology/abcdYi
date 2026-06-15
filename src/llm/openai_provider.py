import os
import json
import httpx
from src.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def complete(self, prompt: str, system: str = "") -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def extract_json(self, prompt: str, system: str = "") -> dict:
        text = await self.complete(prompt, system)
        try:
            return json.loads(text)
        except Exception:
            return {"_error": "JSON parse failed", "_raw": text}
