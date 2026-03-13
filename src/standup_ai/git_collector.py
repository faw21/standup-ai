"""Collect git commits from one or more repositories within a time window."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Iterator

import git


@dataclass(frozen=True)
class CommitInfo:
    repo_name: str
    repo_path: str
    sha: str
    message: str
    author: str
    timestamp: datetime
    files_changed: list[str]


def _find_git_repos(root: Path, max_depth: int = 2) -> Iterator[Path]:
    """Recursively find git repos under root up to max_depth levels deep."""
    if (root / ".git").exists():
        yield root
        return  # don't recurse into nested repos
    if max_depth <= 0:
        return
    if not root.exists():
        return
    try:
        for child in sorted(root.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                yield from _find_git_repos(child, max_depth - 1)
    except PermissionError:
        pass


def collect_commits(
    paths: list[str],
    since: datetime,
    until: datetime | None = None,
    author_filter: str | None = None,
    max_repos: int = 20,
) -> list[CommitInfo]:
    """Collect commits from all git repos under the given paths since the given time.

    Args:
        paths: List of directory paths to search for git repos.
        since: Only include commits after this timestamp.
        until: Only include commits before this timestamp (optional).
        author_filter: If set, only include commits by this author (substring match).
        max_repos: Max number of repos to scan.

    Returns:
        List of CommitInfo sorted by timestamp descending.
    """
    result: list[CommitInfo] = []
    seen_repos: set[str] = set()

    for raw_path in paths:
        root = Path(raw_path).expanduser().resolve()
        if not root.exists():
            continue
        for repo_path in _find_git_repos(root):
            canonical = str(repo_path)
            if canonical in seen_repos:
                continue
            seen_repos.add(canonical)
            if len(seen_repos) > max_repos:
                break

            try:
                repo = git.Repo(repo_path)
                repo_name = repo_path.name
                result.extend(
                    _collect_from_repo(repo, repo_name, str(repo_path), since, until, author_filter)
                )
            except (git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError):
                continue

    result.sort(key=lambda c: c.timestamp, reverse=True)
    return result


def _collect_from_repo(
    repo: git.Repo,
    repo_name: str,
    repo_path: str,
    since: datetime,
    until: datetime | None,
    author_filter: str | None,
) -> list[CommitInfo]:
    """Collect commits from a single repo."""
    commits: list[CommitInfo] = []
    try:
        iter_kwargs: dict = {"since": since.isoformat()}
        if until is not None:
            iter_kwargs["until"] = until.isoformat()
        for commit in repo.iter_commits(**iter_kwargs):
            if author_filter and author_filter.lower() not in commit.author.name.lower():
                if author_filter.lower() not in commit.author.email.lower():
                    continue

            # get changed files (handle merge commits gracefully)
            files_changed: list[str] = []
            try:
                if commit.parents:
                    diff = commit.diff(commit.parents[0])
                    files_changed = [d.a_path or d.b_path for d in diff]
                else:
                    files_changed = list(commit.stats.files.keys())
            except Exception:
                files_changed = list(commit.stats.files.keys())

            # make timestamp timezone-aware
            ts = commit.authored_datetime
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            commits.append(
                CommitInfo(
                    repo_name=repo_name,
                    repo_path=repo_path,
                    sha=commit.hexsha[:8],
                    message=commit.message.strip(),
                    author=commit.author.name,
                    timestamp=ts,
                    files_changed=files_changed,
                )
            )
    except (ValueError, git.GitCommandError):
        pass
    return commits


def get_default_since(hours: int = 24) -> datetime:
    """Return a timezone-aware datetime N hours ago."""
    return datetime.now(tz=timezone.utc) - timedelta(hours=hours)


def get_yesterday_range() -> tuple[datetime, datetime]:
    """Return (start, end) for yesterday in local time, as UTC-aware datetimes."""
    local_tz = datetime.now().astimezone().tzinfo
    today = date.today()
    yesterday = today - timedelta(days=1)
    since = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=local_tz)
    until = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=local_tz)
    return since, until


def get_days_range(n: int) -> datetime:
    """Return start-of-day N days ago in local time, as a UTC-aware datetime."""
    local_tz = datetime.now().astimezone().tzinfo
    target = date.today() - timedelta(days=n)
    return datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=local_tz)


def get_current_author(paths: list[str]) -> str | None:
    """Try to get git user.name from config."""
    for raw_path in paths:
        root = Path(raw_path).expanduser().resolve()
        for repo_path in _find_git_repos(root):
            try:
                repo = git.Repo(repo_path)
                name = repo.config_reader().get_value("user", "name", None)
                if name:
                    return str(name)
            except Exception:
                continue
    # fall back to git global config
    try:
        import subprocess
        result = subprocess.run(
            ["git", "config", "--global", "user.name"],
            capture_output=True, text=True, timeout=5
        )
        name = result.stdout.strip()
        if name:
            return name
    except Exception:
        pass
    return None
