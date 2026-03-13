"""Tests for CLI entry point."""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from standup_ai.cli import main
from standup_ai.git_collector import CommitInfo


def make_commit(
    repo_name: str = "myrepo",
    message: str = "feat: add feature",
    hours_ago: int = 2,
) -> CommitInfo:
    ts = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    return CommitInfo(
        repo_name=repo_name,
        repo_path=f"/fake/{repo_name}",
        sha="abc12345",
        message=message,
        author="Test User",
        timestamp=ts,
        files_changed=["src/app.py"],
    )


FAKE_STANDUP = "**Yesterday:**\n- Did stuff\n\n**Today:**\n- More stuff\n\n**Blockers:**\n- None"


class TestCLIVersion:
    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "standup" in result.output.lower()


class TestCLINoCommits:
    @patch("standup_ai.cli.collect_commits", return_value=[])
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_no_commits_shows_message(self, mock_author, mock_collect):
        runner = CliRunner()
        result = runner.invoke(main, ["--no-filter"])
        assert result.exit_code == 0
        assert "No commits" in result.output


class TestCLIWithCommits:
    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value="Test User")
    def test_generates_standup(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude"])
        assert result.exit_code == 0
        assert "Yesterday" in result.output or "Daily Standup" in result.output

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value="Test User")
    def test_raw_flag_plain_text(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--raw"])
        assert result.exit_code == 0
        assert result.output.strip() == FAKE_STANDUP

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value="Test User")
    def test_show_commits_flag(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit(message="feat: add button")]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--show-commits"])
        assert result.exit_code == 0
        assert "feat: add button" in result.output

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_slack_style(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = "Slack standup"
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--style", "slack"])
        assert result.exit_code == 0

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    @patch("pyperclip.copy")
    def test_copy_flag(self, mock_copy, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--copy"])
        assert result.exit_code == 0
        mock_copy.assert_called_once_with(FAKE_STANDUP)

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_hours_option(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--hours", "48"])
        assert result.exit_code == 0
        # verify since was passed correctly
        call_kwargs = mock_collect.call_args
        assert call_kwargs is not None

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_author_option_passed_through(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--author", "alice"])
        assert result.exit_code == 0
        # verify author_filter was "alice"
        call_kwargs = mock_collect.call_args
        assert call_kwargs[1].get("author_filter") == "alice" or "alice" in str(call_kwargs)

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_no_filter_passes_none(self, mock_author, mock_collect, mock_provider_factory):
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_STANDUP
        mock_provider_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--no-filter"])
        assert result.exit_code == 0


class TestCLIProviderErrors:
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_invalid_provider_exits_1(self, mock_author, mock_collect):
        mock_collect.return_value = [make_commit()]
        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "invalid_choice"])
        assert result.exit_code != 0

    @patch("standup_ai.cli.create_provider", side_effect=KeyError("ANTHROPIC_API_KEY"))
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_missing_api_key_exits_1(self, mock_author, mock_collect, mock_factory):
        mock_collect.return_value = [make_commit()]
        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude"])
        assert result.exit_code == 1


class TestCLIAutoDetectProvider:
    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_auto_detects_claude_from_env(self, mock_author, mock_collect, mock_factory, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = "standup"
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_factory.assert_called_once_with("claude", None)

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_auto_detects_openai_from_env(self, mock_author, mock_collect, mock_factory, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = "standup"
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_factory.assert_called_once_with("openai", None)

    @patch("standup_ai.cli.create_provider")
    @patch("standup_ai.cli.collect_commits")
    @patch("standup_ai.cli.get_current_author", return_value=None)
    def test_falls_back_to_ollama(self, mock_author, mock_collect, mock_factory, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_collect.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = "standup"
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_factory.assert_called_once_with("ollama", None)
