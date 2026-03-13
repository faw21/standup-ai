"""LLM provider abstraction — Claude, OpenAI, Ollama."""

from __future__ import annotations

import os
from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str:
        ...


class ClaudeProvider:
    def __init__(self, model: str = "claude-haiku-4-5-20251001", api_key: str | None = None):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model

    def complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text


class OpenAIProvider:
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=1024,
        )
        return resp.choices[0].message.content or ""


class OllamaProvider:
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url

    def complete(self, system: str, user: str) -> str:
        import urllib.request
        import json

        payload = json.dumps({
            "model": self._model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")


def create_provider(provider: str, model: str | None = None) -> LLMProvider:
    """Factory — create the right LLM provider."""
    provider = provider.lower()
    if provider == "claude":
        m = model or "claude-haiku-4-5-20251001"
        return ClaudeProvider(model=m)
    elif provider == "openai":
        m = model or "gpt-4o-mini"
        return OpenAIProvider(model=m)
    elif provider == "ollama":
        m = model or "llama3.2"
        return OllamaProvider(model=m)
    else:
        raise ValueError(f"Unknown provider: {provider!r}. Choose: claude, openai, ollama")
