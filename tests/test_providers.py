"""Tests for LLM providers."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from standup_ai.providers import create_provider, ClaudeProvider, OpenAIProvider, OllamaProvider


class TestCreateProvider:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("unknown_xyz")

    def test_create_claude(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        with patch("anthropic.Anthropic"):
            p = create_provider("claude")
        assert isinstance(p, ClaudeProvider)

    def test_create_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        with patch("openai.OpenAI"):
            p = create_provider("openai")
        assert isinstance(p, OpenAIProvider)

    def test_create_ollama(self):
        p = create_provider("ollama")
        assert isinstance(p, OllamaProvider)

    def test_create_claude_custom_model(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        with patch("anthropic.Anthropic"):
            p = create_provider("claude", model="claude-sonnet-4-6")
        assert isinstance(p, ClaudeProvider)
        assert p._model == "claude-sonnet-4-6"

    def test_create_openai_custom_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        with patch("openai.OpenAI"):
            p = create_provider("openai", model="gpt-4o")
        assert isinstance(p, OpenAIProvider)
        assert p._model == "gpt-4o"

    def test_create_ollama_custom_model(self):
        p = create_provider("ollama", model="mistral")
        assert isinstance(p, OllamaProvider)
        assert p._model == "mistral"

    def test_case_insensitive_provider(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        with patch("anthropic.Anthropic"):
            p = create_provider("Claude")
        assert isinstance(p, ClaudeProvider)


class TestClaudeProvider:
    def test_complete_calls_api(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="standup text")]
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            p = ClaudeProvider()

        result = p.complete("system", "user")
        assert result == "standup text"
        mock_client.messages.create.assert_called_once()


class TestOpenAIProvider:
    def test_complete_calls_api(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "openai standup"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider()

        result = p.complete("system", "user")
        assert result == "openai standup"


class TestOllamaProvider:
    def test_complete_calls_api(self):
        import json
        from unittest.mock import patch as p

        mock_response_data = json.dumps({"response": "ollama standup"}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            provider = OllamaProvider(model="llama3.2")
            result = provider.complete("system", "user")

        assert result == "ollama standup"
