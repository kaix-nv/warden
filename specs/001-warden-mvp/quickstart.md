# Quickstart: Warden MVP

**Date**: 2026-04-12

## Prerequisites

- Python 3.11+
- Git
- `gh` CLI (authenticated with GitHub) — required for PR reading/creation features
- Claude Code authentication configured (Agent SDK uses existing Claude Code auth)

## Install

```bash
pip install warden-ai
```

Or for development:

```bash
git clone <repo-url>
cd warden
pip install -e ".[dev]"
```

## Initialize on your repository

```bash
cd /path/to/your/repo
warden init
```

This will:
1. Create `.warden/` directory with default configuration
2. Scan your full repository history (commits + merged PRs)
3. Generate understanding documents: `architecture.md`, `design-decisions.md`, `patterns.md`
4. Install a post-commit hook for automatic analysis
5. Add `state.db` to `.gitignore`

## Work normally — Warden watches automatically

After initialization, just commit as usual. Warden analyzes each commit in the background via the post-commit hook.

To manually process any unanalyzed commits:

```bash
warden analyze
```

To process a specific commit:

```bash
warden analyze --commit abc123
```

## Ask questions about your codebase

```bash
warden ask "Why do we use connection pooling for the session store?"
warden ask "What patterns does this project follow for error handling?"
warden ask "When was the authentication system redesigned and why?"
```

## Check Warden's status

```bash
warden status
```

Shows: commits processed, last analysis date, document sizes, pending draft PRs.

## Review Warden's draft PRs

When Warden finds issues during review, it creates draft PRs automatically. Review them on GitHub at your convenience. Warden never merges — you decide.

## Configure

Edit `.warden/config.yml` to customize behavior:

```bash
warden config           # Show current config
warden config validate  # Check for errors
```

Common customizations:
- Disable automated review: set `review.enabled: false`
- Limit draft PRs: set `review.max_draft_prs: 3`
- Add ignore patterns: append to `git.ignore_patterns`

## Reset

```bash
warden reset --understanding    # Clear understanding docs (re-run init to rebuild)
warden reset --improvements     # Clear improvement history
warden reset --all              # Full reset
```
