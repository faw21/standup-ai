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
from .git_collector import collect_commits, get_default_since, get_current_author
from .generator import generate_standup
from .providers import create_provider

console = Console()
err_console = Console(stderr=True)


def _resolve_paths(paths: tuple[str, ...]) -> list[str]:
    if paths:
        return list(paths)
    # default: current directory
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
    default=24,
    show_default=True,
    help="How many hours back to look for commits.",
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
    default="standard",
    show_default=True,
    help="Output style.",
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
    hours: int,
    author: str | None,
    provider: str | None,
    model: str | None,
    style: str,
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
      standup-ai --hours 48               # look back 2 days
      standup-ai --style slack --copy     # Slack format, copy to clipboard
      standup-ai --provider ollama        # use local Ollama (no API key needed)
    """
    resolved_paths = _resolve_paths(paths)
    since = get_default_since(hours)

    # resolve author filter
    author_filter: str | None = None
    if not no_filter:
        if author:
            author_filter = author
        else:
            detected = get_current_author(resolved_paths)
            if detected:
                author_filter = detected

    # resolve provider
    chosen_provider = provider or _auto_detect_provider()

    # collect commits
    with console.status("[bold green]Scanning git history...[/bold green]"):
        commits = collect_commits(resolved_paths, since=since, author_filter=author_filter)

    if show_commits:
        if commits:
            console.print(f"\n[dim]Found {len(commits)} commit(s):[/dim]")
            for c in commits:
                console.print(f"  [cyan]{c.repo_name}[/cyan] [{c.sha}] {c.message.splitlines()[0]}")
        else:
            console.print("[yellow]No commits found.[/yellow]")

    if not commits:
        console.print(
            Panel(
                "[yellow]No commits found in the last "
                f"{hours} hour(s).[/yellow]\n\n"
                "Try [bold]--hours 48[/bold] to look further back, or "
                "[bold]--no-filter[/bold] to include all authors.",
                title="standup-ai",
                border_style="yellow",
            )
        )
        sys.exit(0)

    # generate standup
    try:
        llm = create_provider(chosen_provider, model)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyError as e:
        err_console.print(f"[red]Missing API key:[/red] {e}")
        sys.exit(1)

    with console.status(f"[bold green]Generating standup with {chosen_provider}...[/bold green]"):
        try:
            standup_text = generate_standup(commits, llm, style=style)
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
                title=f"[bold]Daily Standup[/bold] [dim]({style})[/dim]",
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
