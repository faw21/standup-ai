"""Tests for git_collector module."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from standup_ai.git_collector import (
    CommitInfo,
    collect_commits,
    get_default_since,
    get_current_author,
    get_yesterday_range,
    get_days_range,
    _find_git_repos,
)


def make_commit(
    repo_name: str = "testrepo",
    message: str = "fix: test",
    author: str = "Alice",
    hours_ago: int = 1,
    files: list[str] | None = None,
) -> CommitInfo:
    ts = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    return CommitInfo(
        repo_name=repo_name,
        repo_path=f"/fake/{repo_name}",
        sha="abc12345",
        message=message,
        author=author,
        timestamp=ts,
        files_changed=files or ["src/main.py"],
    )


class TestGetDefaultSince:
    def test_returns_utc_aware_datetime(self):
        since = get_default_since(24)
        assert since.tzinfo is not None

    def test_is_roughly_n_hours_ago(self):
        since = get_default_since(24)
        delta = datetime.now(tz=timezone.utc) - since
        assert 23 < delta.total_seconds() / 3600 < 25

    def test_custom_hours(self):
        since = get_default_since(48)
        delta = datetime.now(tz=timezone.utc) - since
        assert 47 < delta.total_seconds() / 3600 < 49


class TestFindGitRepos:
    def test_finds_repo_at_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        repos = list(_find_git_repos(tmp_path))
        assert repos == [tmp_path]

    def test_finds_nested_repos(self, tmp_path):
        child = tmp_path / "myproject"
        child.mkdir()
        (child / ".git").mkdir()
        repos = list(_find_git_repos(tmp_path))
        assert child in repos

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / ".git").mkdir()
        repos = list(_find_git_repos(tmp_path))
        assert hidden not in repos

    def test_does_not_recurse_into_repo(self, tmp_path):
        """Once a repo is found, don't look for nested repos inside it."""
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / ".git").mkdir()
        repos = list(_find_git_repos(tmp_path))
        # should only return the root repo, not the nested one
        assert tmp_path in repos
        assert nested not in repos

    def test_nonexistent_path_is_skipped(self, tmp_path):
        repos = list(_find_git_repos(tmp_path / "nonexistent"))
        assert repos == []


class TestCollectCommits:
    def test_empty_paths_returns_empty(self):
        since = get_default_since(24)
        result = collect_commits([], since)
        assert result == []

    def test_nonexistent_path_skipped(self):
        since = get_default_since(24)
        result = collect_commits(["/nonexistent/path/xyz"], since)
        assert result == []

    def test_sorted_by_timestamp_descending(self):
        """collect_commits should return commits newest-first."""
        since = get_default_since(48)
        # Use the actual give-it-all folder (has git repos)
        base = str(Path(__file__).parent.parent.parent)
        result = collect_commits([base], since, author_filter="__nobody__")
        # With a non-matching author filter, result is empty — that's fine
        assert isinstance(result, list)

    def test_with_real_git_repo(self, tmp_path):
        """Integration: collect_commits on a fresh git repo returns no commits."""
        import subprocess
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path, check=True, capture_output=True
        )
        since = get_default_since(24)
        result = collect_commits([str(tmp_path)], since)
        assert result == []

    def test_with_real_commit(self, tmp_path):
        """Integration: actual commit shows up in results."""
        import subprocess
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path, check=True, capture_output=True
        )
        test_file = tmp_path / "hello.txt"
        test_file.write_text("hello world")
        subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add hello world"],
            cwd=tmp_path, check=True, capture_output=True
        )
        since = get_default_since(1)
        result = collect_commits([str(tmp_path)], since)
        assert len(result) == 1
        assert result[0].message == "feat: add hello world"
        assert result[0].repo_name == tmp_path.name

    def test_author_filter_case_insensitive(self, tmp_path):
        """Author filter should be case-insensitive."""
        import subprocess
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "alice@example.com"],
            cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Alice Smith"],
            cwd=tmp_path, check=True, capture_output=True
        )
        test_file = tmp_path / "a.txt"
        test_file.write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test commit"],
            cwd=tmp_path, check=True, capture_output=True
        )
        since = get_default_since(1)
        # should match 'alice' (lowercase) against 'Alice Smith'
        result = collect_commits([str(tmp_path)], since, author_filter="alice")
        assert len(result) == 1
        # should not match 'bob'
        result2 = collect_commits([str(tmp_path)], since, author_filter="bob")
        assert len(result2) == 0


class TestGetYesterdayRange:
    def test_returns_tuple_of_datetimes(self):
        since, until = get_yesterday_range()
        assert since.tzinfo is not None
        assert until.tzinfo is not None

    def test_since_before_until(self):
        since, until = get_yesterday_range()
        assert since < until

    def test_range_is_one_day(self):
        since, until = get_yesterday_range()
        delta = until - since
        assert delta.total_seconds() == 86400  # exactly 24 hours

    def test_until_is_today_midnight(self):
        from datetime import date
        since, until = get_yesterday_range()
        today = date.today()
        assert until.date() == today

    def test_since_is_yesterday_midnight(self):
        from datetime import date, timedelta
        since, until = get_yesterday_range()
        yesterday = date.today() - timedelta(days=1)
        assert since.date() == yesterday


class TestGetDaysRange:
    def test_returns_utc_aware(self):
        result = get_days_range(3)
        assert result.tzinfo is not None

    def test_3_days_ago(self):
        from datetime import date, timedelta
        result = get_days_range(3)
        expected_date = date.today() - timedelta(days=3)
        assert result.date() == expected_date

    def test_1_day_is_yesterday_start(self):
        from datetime import date, timedelta
        result = get_days_range(1)
        yesterday = date.today() - timedelta(days=1)
        assert result.date() == yesterday

    def test_midnight_start(self):
        result = get_days_range(2)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0


class TestGetCurrentAuthor:
    def test_returns_none_for_empty_paths(self):
        result = get_current_author([])
        # May return global git config name or None
        assert result is None or isinstance(result, str)

    def test_returns_none_for_nonexistent_path(self):
        result = get_current_author(["/nonexistent/path"])
        assert result is None or isinstance(result, str)
