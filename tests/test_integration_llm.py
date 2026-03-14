"""Real LLM integration tests — calls actual APIs, not mocks.

Run with: pytest tests/test_integration_llm.py -v -s
Uses small/cheap models to save cost.
"""

from __future__ import annotations

import os
import pytest
from dotenv import load_dotenv

load_dotenv("/Users/aaronwu/Local/my-projects/give-it-all/.env", override=True)

from standup_ai.providers import create_provider, ClaudeProvider, OpenAIProvider, OllamaProvider


# ── helpers ─────────────────────────────────────────────────────────────────

SYSTEM = "You are a helpful assistant. Keep responses short."
USER = "Say exactly: 'LLM test OK'"

has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
has_openai = bool(os.environ.get("OPENAI_API_KEY"))


# ── Claude ───────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not has_anthropic, reason="ANTHROPIC_API_KEY not set")
def test_claude_real_call():
    """Real call to Anthropic claude-haiku-4-5."""
    provider = ClaudeProvider(model="claude-haiku-4-5-20251001")
    result = provider.complete(SYSTEM, USER)
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"\n[Claude] response: {result!r}")


@pytest.mark.skipif(not has_anthropic, reason="ANTHROPIC_API_KEY not set")
def test_create_provider_claude_real():
    """Factory creates Claude provider and calls API."""
    provider = create_provider("claude", model="claude-haiku-4-5-20251001")
    result = provider.complete(SYSTEM, USER)
    assert isinstance(result, str)
    assert len(result) > 0


# ── OpenAI ───────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not has_openai, reason="OPENAI_API_KEY not set")
def test_openai_real_call():
    """Real call to OpenAI gpt-5-nano."""
    provider = OpenAIProvider(model="gpt-5-nano")
    result = provider.complete(SYSTEM, USER)
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"\n[OpenAI] response: {result!r}")


@pytest.mark.skipif(not has_openai, reason="OPENAI_API_KEY not set")
def test_create_provider_openai_real():
    """Factory creates OpenAI provider and calls API."""
    provider = create_provider("openai", model="gpt-5-nano")
    result = provider.complete(SYSTEM, USER)
    assert isinstance(result, str)
    assert len(result) > 0


# ── Ollama ───────────────────────────────────────────────────────────────────

def test_ollama_real_call():
    """Real call to local Ollama qwen2.5:1.5b (no API key needed)."""
    provider = OllamaProvider(model="qwen2.5:1.5b")
    result = provider.complete(SYSTEM, USER)
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"\n[Ollama] response: {result!r}")


def test_create_provider_ollama_real():
    """Factory creates Ollama provider and calls API."""
    provider = create_provider("ollama", model="qwen2.5:1.5b")
    result = provider.complete(SYSTEM, USER)
    assert isinstance(result, str)
    assert len(result) > 0
