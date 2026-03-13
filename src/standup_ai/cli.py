"""CLI entry point for standup-ai."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from . import __version__
from .git_collector import collect_commits, get_default_since, get_current_author, get_yesterday_range, get_days_range
from .generator import generate_standup
from .providers import create_provider
from .config import load_config, get_config_value

console = Console()
err_console = Console(stderr=True)


def _resolve_paths(paths: tuple[str, ...], config: dict) -> list[str]:
    if paths:
        return list(paths)
    config_paths = get_config_value(config, "paths")
    if config_paths and isinstance(config_paths, list):
        return [str(p) for p in config_paths]
    return ["."]


def _auto_detect_provider() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "ollama"


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("paths", nargs=-1, metavar="[PATH...]")
@click.option(
    "--hours",
    default=None,
    type=int,
    show_default=False,
    help="How many hours back to look for commits. Default: 24.",
)
@click.option(
    "--yesterday",
    is_flag=True,
    help="Only include commits from yesterday (midnight to midnight, local time).",
)
@click.option(
    "--days",
    default=None,
    type=int,
    help="Look back N calendar days (from start of day N days ago until now).",
)
@click.option(
    "--author",
    default=None,
    help="Filter commits by author name/email (substring). Auto-detected from git config if not set.",
)
@click.option(
    "--provider",
    type=click.Choice(["claude", "openai", "ollama"], case_sensitive=False),
    default=None,
    help="LLM provider. Auto-detected from environment if not set.",
)
@click.option(
    "--model",
    default=None,
    help="LLM model name (overrides provider default).",
)
@click.option(
    "--style",
    type=click.Choice(["standard", "bullet", "slack"], case_sensitive=False),
    default=None,
    show_default=False,
    help="Output style. Default: standard.",
)
@click.option(
    "--copy",
    is_flag=True,
    help="Copy output to clipboard.",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Print raw text only (no rich formatting). Useful for piping.",
)
@click.option(
    "--no-filter",
    is_flag=True,
    help="Include all authors (don't filter to current user).",
)
@click.option(
    "--show-commits",
    is_flag=True,
    help="Print the raw commits found before generating standup.",
)
@click.version_option(__version__, "-V", "--version")
def main(
    paths: tuple[str, ...],
    hours: int | None,
    yesterday: bool,
    days: int | None,
    author: str | None,
    provider: str | None,
    model: str | None,
    style: str | None,
    copy: bool,
    raw: bool,
    no_filter: bool,
    show_commits: bool,
) -> None:
    """Generate your daily standup from git commits using AI.

    Scans git history from PATH(s) (default: current directory) and generates
    a professional standup update you can paste into Slack or your daily sync.

    \b
    Examples:
      standup-ai                          # scan current dir, auto-detect provider
      standup-ai ~/projects ~/work        # scan multiple project directories
      standup-ai --yesterday              # only commits from yesterday
      standup-ai --days 3                 # last 3 calendar days
      standup-ai --hours 48               # look back 48 hours
      standup-ai --style slack --copy     # Slack format, copy to clipboard
      standup-ai --provider ollama        # use local Ollama (no API key needed)
    """
    # mutually exclusive time flags
    time_flags = sum([bool(hours), yesterday, bool(days)])
    if time_flags > 1:
        err_console.print("[red]Error:[/red] --hours, --yesterday, and --days are mutually exclusive.")
        sys.exit(1)

    # load config
    config = load_config()

    resolved_paths = _resolve_paths(paths, config)

    # resolve time window
    since: datetime
    until: datetime | None = None

    if yesterday:
        since, until = get_yesterday_range()
    elif days is not None:
        since = get_days_range(days)
    else:
        effective_hours = hours or get_config_value(config, "hours", 24)
        since = get_default_since(effective_hours)

    # resolve style (CLI > config > default)
    effective_style = style or get_config_value(config, "style", "standard")

    # resolve author filter
    author_filter: str | None = None
    if not no_filter:
        if author:
            author_filter = author
        else:
            config_author = get_config_value(config, "author")
            if config_author:
                author_filter = str(config_author)
            else:
                detected = get_current_author(resolved_paths)
                if detected:
                    author_filter = detected

    # resolve provider
    config_provider = get_config_value(config, "provider")
    config_model = get_config_value(config, "model")
    chosen_provider = provider or config_provider or _auto_detect_provider()
    effective_model = model or config_model or None

    # collect commits
    with console.status("[bold green]Scanning git history...[/bold green]"):
        commits = collect_commits(resolved_paths, since=since, until=until, author_filter=author_filter)

    if show_commits:
        if commits:
            console.print(f"\n[dim]Found {len(commits)} commit(s):[/dim]")
            for c in commits:
                console.print(f"  [cyan]{c.repo_name}[/cyan] [{c.sha}] {c.message.splitlines()[0]}")
        else:
            console.print("[yellow]No commits found.[/yellow]")

    if not commits:
        # build a user-friendly time description
        if yesterday:
            time_desc = "yesterday"
        elif days is not None:
            time_desc = f"the last {days} day(s)"
        else:
            effective_hours = hours or get_config_value(config, "hours", 24)
            time_desc = f"the last {effective_hours} hour(s)"

        console.print(
            Panel(
                f"[yellow]No commits found in {time_desc}.[/yellow]\n\n"
                "Try [bold]--days 3[/bold] to look further back, or "
                "[bold]--no-filter[/bold] to include all authors.",
                title="standup-ai",
                border_style="yellow",
            )
        )
        sys.exit(0)

    # generate standup
    try:
        llm = create_provider(chosen_provider, effective_model)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyError as e:
        err_console.print(f"[red]Missing API key:[/red] {e}")
        sys.exit(1)

    with console.status(f"[bold green]Generating standup with {chosen_provider}...[/bold green]"):
        try:
            standup_text = generate_standup(commits, llm, style=effective_style)
        except Exception as e:
            err_console.print(f"[red]LLM error:[/red] {e}")
            sys.exit(1)

    # output
    if raw:
        click.echo(standup_text)
    else:
        repo_names = sorted({c.repo_name for c in commits})
        subtitle = f"{len(commits)} commit(s) · {', '.join(repo_names[:3])}" + (
            f" +{len(repo_names) - 3} more" if len(repo_names) > 3 else ""
        )
        console.print()
        console.print(
            Panel(
                Markdown(standup_text),
                title=f"[bold]Daily Standup[/bold] [dim]({effective_style})[/dim]",
                subtitle=f"[dim]{subtitle}[/dim]",
                border_style="green",
            )
        )

    # clipboard
    if copy:
        try:
            import pyperclip
            pyperclip.copy(standup_text)
            if not raw:
                console.print("[dim]✓ Copied to clipboard[/dim]")
        except Exception as e:
            err_console.print(f"[yellow]Clipboard failed:[/yellow] {e}")
