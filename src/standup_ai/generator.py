"""Generate standup text from commit data."""

from __future__ import annotations

from .git_collector import CommitInfo
from .providers import LLMProvider


SYSTEM_PROMPT = """\
You are a senior software engineer writing a concise daily standup update.
Based on the git commits provided, write a professional standup in plain text.

Format:
**Yesterday:**
- [what was accomplished, grouped by project/feature]

**Today:**
- [reasonable next steps based on yesterday's work]

**Blockers:**
- None (or infer from commit patterns if obvious)

Rules:
- Be concise — no more than 5 bullet points per section
- Group related work together (don't list every commit separately)
- Use plain, professional language
- If commits are from multiple repos, mention repo names in brackets like [repo-name]
- Don't mention commit hashes
- If no commits found, say "No commits found in the time window."
"""


def build_commit_summary(commits: list[CommitInfo]) -> str:
    """Build a compact text representation of commits for the LLM."""
    if not commits:
        return "No commits found in the specified time window."

    lines: list[str] = []
    for c in commits:
        files_str = ", ".join(c.files_changed[:5])
        if len(c.files_changed) > 5:
            files_str += f" (+{len(c.files_changed) - 5} more)"
        lines.append(
            f"[{c.repo_name}] {c.sha} — {c.message.splitlines()[0]}"
            + (f"\n  Files: {files_str}" if files_str else "")
        )
    return "\n".join(lines)


def generate_standup(
    commits: list[CommitInfo],
    provider: LLMProvider,
    style: str = "standard",
) -> str:
    """Generate standup text from commits using the given LLM provider.

    Args:
        commits: List of commit info from git_collector.
        provider: LLM provider instance.
        style: Output style — 'standard', 'bullet', or 'slack'.

    Returns:
        Standup text as a string.
    """
    commit_summary = build_commit_summary(commits)

    style_hints = {
        "standard": "Use the format described above with Yesterday/Today/Blockers sections.",
        "bullet": "Use only flat bullet points, no section headers. Keep it ultra-brief (3-5 bullets total).",
        "slack": "Write as a single Slack message. Start with a 1-line summary, then a brief bullet list. Use emoji sparingly (1-2 max). No markdown headers.",
    }
    hint = style_hints.get(style, style_hints["standard"])

    user_prompt = f"""\
Here are my git commits from the past 24 hours:

{commit_summary}

{hint}

Write the standup now:"""

    return provider.complete(SYSTEM_PROMPT, user_prompt)
