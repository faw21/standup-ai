# standup-ai

> Generate your daily standup from git history — in seconds.

```bash
standup-ai                         # scan current dir, auto-detect provider
standup-ai --yesterday             # only commits from yesterday
standup-ai --days 3                # last 3 calendar days
standup-ai --style slack --copy    # Slack format, copy to clipboard
standup-ai --provider ollama       # no API key needed
```

[![PyPI version](https://img.shields.io/pypi/v/standup-ai.svg)](https://pypi.org/project/standup-ai/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen.svg)](https://github.com/faw21/standup-ai)

---

## The problem

Every developer on a remote team has to write a daily standup:
> "Yesterday I worked on auth, fixed a bug in the login flow, started the JWT implementation. Today I'll finish JWT and write tests."

You already *did* the work. Why are you also *writing* about it?

**`standup-ai` reads your git commits and writes the standup for you.**

---

## Demo

```
$ standup-ai ~/projects --style slack --copy

╭─────────────────────────── Daily Standup (slack) ──────────────────────────╮
│                                                                              │
│  Shipped JWT auth and fixed two production bugs                              │
│                                                                              │
│  • [gitbrief] Added --changed-only flag for PR review mode                  │
│  • [gitbrief] Implemented git diff embedding with --include-diff            │
│  • [api-service] Fixed null pointer in /users/profile endpoint              │
│  • Today: finish JWT refresh token rotation, write integration tests        │
│                                                                              │
╰──────────────────────────── 4 commits · gitbrief, api-service ─────────────╯

✓ Copied to clipboard
```

---

## Why standup-ai?

[git-standup](https://github.com/kamranahmedse/git-standup) (6k stars) is the closest thing — it lists raw commits from the last 24 hours. Great for finding what you did, but you still have to write the standup yourself.

`standup-ai` goes further:

| Feature | standup-ai | git-standup | manual |
|---------|-----------|-------------|--------|
| Scans multiple repos | ✅ | ✅ | ❌ |
| AI-generated summary | ✅ | ❌ | ❌ |
| Slack/bullet/standard styles | ✅ | ❌ | ❌ |
| Auto-detects your author | ✅ | ✅ | ❌ |
| Clipboard copy | ✅ | ❌ | ❌ |
| Works with local LLMs | ✅ | ❌ | ❌ |
| No API key required (Ollama) | ✅ | ✅ | ✅ |

---

## Install

```bash
pip install standup-ai
```

Or with [pipx](https://pipx.pypa.io/) (recommended):
```bash
pipx install standup-ai
```

Requires Python 3.9+.

---

## Quick Start

```bash
# Auto-detects provider from env (ANTHROPIC_API_KEY or OPENAI_API_KEY)
standup-ai

# Scan multiple project directories
standup-ai ~/projects ~/side-projects

# Only commits from yesterday (great for morning standups)
standup-ai --yesterday

# Last 3 calendar days (e.g. Monday morning covering the weekend)
standup-ai --days 3

# Slack format, copy to clipboard
standup-ai --style slack --copy

# No API key needed — use Ollama
standup-ai --provider ollama --model llama3.2

# Show raw commits before generating
standup-ai --show-commits

# Raw output for piping
standup-ai --raw > standup.txt
```

---

## Config File

Save your defaults in `~/.standup.yaml` so you never have to type them again:

```yaml
# ~/.standup.yaml
paths:
  - ~/projects
  - ~/work
style: slack
provider: claude
# author: "Your Name"   # override git user.name
# hours: 24             # default time window
```

Any CLI flag still overrides the config file.

---

## Providers

| Provider | Flag | Requires |
|----------|------|---------|
| Claude (default if key exists) | `--provider claude` | `ANTHROPIC_API_KEY` |
| OpenAI | `--provider openai` | `OPENAI_API_KEY` |
| Ollama (local, free) | `--provider ollama` | [Ollama](https://ollama.ai) running |

### Using Ollama (no API key)

```bash
# Install Ollama: https://ollama.ai
ollama pull llama3.2

standup-ai --provider ollama --model llama3.2
```

---

## Output Styles

### --style standard (default)

```
**Yesterday:**
- [myrepo] Implemented JWT authentication with refresh token rotation
- [api-service] Fixed null pointer exception in profile endpoint

**Today:**
- Write integration tests for JWT flow
- Code review on open PRs

**Blockers:**
- None
```

### --style bullet

```
- Added JWT auth and refresh tokens [myrepo]
- Fixed profile endpoint bug [api-service]
- Today: integration tests + PR reviews
```

### --style slack

```
Shipped JWT auth and fixed a prod bug

* [myrepo] JWT authentication with refresh token rotation
* [api-service] Profile endpoint null pointer fix
* Today: tests + code review
```

---

## Options

```
standup-ai [PATH...] [OPTIONS]

Arguments:
  PATH...           Directories to scan (default: current directory or ~/.standup.yaml paths)

Time window (mutually exclusive):
  --yesterday       Only commits from yesterday (midnight to midnight, local time)
  --days INT        Last N calendar days (from start of day N days ago)
  --hours INT       How many hours back to look [default: 24]

Options:
  --author TEXT     Filter by author name/email (auto-detected if not set)
  --no-filter       Include all authors (don't filter to current user)
  --provider        claude | openai | ollama (auto-detected from env)
  --model TEXT      Override model name
  --style           standard | bullet | slack [default: standard]
  --copy            Copy output to clipboard
  --raw             Plain text output (no formatting)
  --show-commits    Print raw commits found before generating
  -V, --version     Show version
  -h, --help        Show this message and exit
```

---

## Tips

```bash
# Monday morning standup (covers the weekend)
standup-ai --yesterday --days 3

# Monday morning — all commits since Friday
standup-ai --days 3

# Team standup: see what everyone did (no author filter)
standup-ai --no-filter

# Add to your shell as an alias
alias standup='standup-ai --yesterday --style slack --copy'

# See what commits were found before generating
standup-ai --show-commits --provider ollama
```

---

## Development

```bash
git clone https://github.com/faw21/standup-ai
cd standup-ai
python -m venv .venv && source .venv/bin/activate
.venv/bin/pip install -e ".[dev]"
pytest tests/   # 83 tests, 89% coverage
```

---

## Related Tools

**[gitbrief](https://github.com/faw21/gitbrief)** — Pack the right files from any repo into LLM-ready context using git history.

**[gpr](https://github.com/faw21/gpr)** — AI-powered PR descriptions and commit messages from your git diff.

**[critiq](https://github.com/faw21/critiq)** — AI code reviewer that runs locally before you push. Catches bugs and security issues.

**[changelog-ai](https://github.com/faw21/changelog-ai)** — Generate CHANGELOG entries from git history using AI.

**[git-chronicle](https://github.com/faw21/chronicle)** — AI-powered git history narrator. Turns your git log into engaging stories (narrative, timeline, or detective mode).

**[prcat](https://github.com/faw21/prcat)** — AI reviewer for teammates' pull requests. Summarizes, flags risks, and suggests review comments.

```bash
# The full AI-powered git workflow:
standup-ai --yesterday                                    # 1. morning standup
critiq                                                    # 2. AI review before committing
testfix pytest                                            # 3. Auto-fix failing tests
gpr --commit-run                                          # 4. commit with AI message
gitbrief . --changed-only --clipboard                    # 5. pack context for PR review
gpr                                                       # 6. generate PR description
prcat 42                                                  # 7. AI review of teammate's PR
changelog-ai --release-version v1.x.0 --prepend CHANGELOG.md  # 8. update changelog
```

---

- [difftests](https://github.com/faw21/difftests) — AI test generator from git diffs

- [critiq-action](https://github.com/faw21/critiq-action) — critiq as a GitHub Action for CI

- [testfix](https://github.com/faw21/testfix) — AI failing test auto-fixer

- [mergefix](https://github.com/faw21/mergefix) — AI merge conflict resolver: fix all conflicts with one command

## License

MIT
