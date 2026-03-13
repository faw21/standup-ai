"""Tests for standup generator."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from standup_ai.git_collector import CommitInfo
from standup_ai.generator import build_commit_summary, generate_standup


def make_commit(
    repo_name: str = "myrepo",
    message: str = "feat: add feature",
    files: list[str] | None = None,
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
        files_changed=files or ["src/app.py"],
    )


class TestBuildCommitSummary:
    def test_empty_commits(self):
        result = build_commit_summary([])
        assert "No commits" in result

    def test_single_commit(self):
        commit = make_commit(message="fix: resolve null pointer")
        result = build_commit_summary([commit])
        assert "myrepo" in result
        assert "fix: resolve null pointer" in result
        assert "abc12345" in result

    def test_truncates_long_file_lists(self):
        files = [f"file{i}.py" for i in range(10)]
        commit = make_commit(files=files)
        result = build_commit_summary([commit])
        assert "+5 more" in result

    def test_multiple_repos(self):
        commits = [
            make_commit(repo_name="frontend", message="feat: new button"),
            make_commit(repo_name="backend", message="fix: auth bug"),
        ]
        result = build_commit_summary(commits)
        assert "frontend" in result
        assert "backend" in result

    def test_multiline_commit_message_uses_first_line(self):
        commit = make_commit(message="feat: add feature\n\nMore details here\n")
        result = build_commit_summary([commit])
        assert "feat: add feature" in result
        assert "More details here" not in result


class TestGenerateStandup:
    def test_calls_provider(self):
        provider = MagicMock()
        provider.complete.return_value = "**Yesterday:**\n- Did stuff"
        commits = [make_commit()]
        result = generate_standup(commits, provider)
        assert provider.complete.called
        assert "Yesterday" in result

    def test_empty_commits_still_calls_provider(self):
        provider = MagicMock()
        provider.complete.return_value = "No commits found in the time window."
        result = generate_standup([], provider)
        assert provider.complete.called

    def test_style_standard(self):
        provider = MagicMock()
        provider.complete.return_value = "standup text"
        commits = [make_commit()]
        generate_standup(commits, provider, style="standard")
        call_args = provider.complete.call_args
        # user prompt should mention the standard style hint
        assert "Yesterday/Today/Blockers" in call_args[0][1]

    def test_style_bullet(self):
        provider = MagicMock()
        provider.complete.return_value = "- bullet"
        commits = [make_commit()]
        generate_standup(commits, provider, style="bullet")
        call_args = provider.complete.call_args
        assert "ultra-brief" in call_args[0][1]

    def test_style_slack(self):
        provider = MagicMock()
        provider.complete.return_value = "Slack message"
        commits = [make_commit()]
        generate_standup(commits, provider, style="slack")
        call_args = provider.complete.call_args
        assert "Slack" in call_args[0][1]

    def test_unknown_style_falls_back_to_standard(self):
        provider = MagicMock()
        provider.complete.return_value = "fallback"
        commits = [make_commit()]
        generate_standup(commits, provider, style="nonexistent_style")
        # should not raise
        assert provider.complete.called

    def test_commit_summary_included_in_prompt(self):
        provider = MagicMock()
        provider.complete.return_value = "output"
        commits = [make_commit(message="feat: add login flow")]
        generate_standup(commits, provider)
        call_args = provider.complete.call_args
        assert "feat: add login flow" in call_args[0][1]
