# CLI Contract: Warden

**Date**: 2026-04-12
**Feature**: [spec.md](../spec.md)

Warden is a CLI tool. Its primary interface is a set of commands invoked from the terminal. This document defines the command schema, arguments, options, and expected output for each command.

## Commands

### `warden init`

Initialize Warden on the current git repository.

| Aspect | Detail |
| ------ | ------ |
| **Usage** | `warden init [OPTIONS]` |
| **Preconditions** | Current directory is inside a git repository |
| **Side effects** | Creates `.warden/` directory, installs post-commit hook, adds state.db to .gitignore |

**Options**:

| Option | Type | Default | Description |
| ------ | ---- | ------- | ----------- |
| `--pr-count` | int or "all" | config value or "all" | Number of merged PRs to process |
| `--commit-count` | int or "all" | config value or "all" | Number of commits to process |

**Output** (stdout):
- Progress indicators during bootstrap analysis
- Summary: number of commits processed, number of PRs read, documents generated

**Exit codes**:
- 0: Success
- 1: Not a git repository, or `.warden/` already exists (use `warden reset --all` first)

---

### `warden analyze`

Process new commits since last run.

| Aspect | Detail |
| ------ | ------ |
| **Usage** | `warden analyze [OPTIONS]` |
| **Preconditions** | Warden is initialized (`.warden/` exists) |
| **Side effects** | Updates understanding docs, may create branches and draft PRs |

**Options**:

| Option | Type | Default | Description |
| ------ | ---- | ------- | ----------- |
| `--commit` | string | None | Process a specific commit hash only |

**Output** (stdout):
- Number of commits processed
- Documents updated
- Review findings (if any), with draft PR URLs

**Exit codes**:
- 0: Success (including "no new commits to process")
- 1: Warden not initialized

---

### `warden ask`

Query the understanding docs with a natural language question.

| Aspect | Detail |
| ------ | ------ |
| **Usage** | `warden ask "<question>"` |
| **Preconditions** | Warden is initialized and understanding docs exist |
| **Side effects** | None (read-only) |

**Arguments**:

| Argument | Type | Required | Description |
| -------- | ---- | -------- | ----------- |
| question | string | Yes | Natural language question about the codebase |

**Output** (stdout):
- Answer text with citations (commit hashes, PR numbers, file paths)
- "I don't know" when the understanding docs lack sufficient information

**Exit codes**:
- 0: Success
- 1: Warden not initialized or no understanding docs

---

### `warden status`

Show Warden's current state.

| Aspect | Detail |
| ------ | ------ |
| **Usage** | `warden status` |
| **Preconditions** | Warden is initialized |
| **Side effects** | None (read-only) |

**Output** (stdout):
- Commits processed (count and last hash)
- Last run date
- Understanding doc sizes (line count or word count)
- Pending draft PRs (count and URLs)
- Improvement history (accepted/declined counts)

**Exit codes**:
- 0: Success
- 1: Warden not initialized

---

### `warden config`

Show or validate configuration.

| Aspect | Detail |
| ------ | ------ |
| **Usage** | `warden config [SUBCOMMAND]` |
| **Preconditions** | Warden is initialized |
| **Side effects** | None (read-only) |

**Subcommands**:

| Subcommand | Description |
| ---------- | ----------- |
| (none) | Show current configuration |
| `validate` | Check configuration for errors |

**Output** (stdout):
- Current config as YAML (default)
- Validation results: "OK" or list of errors with line references

**Exit codes**:
- 0: Config is valid
- 1: Config has errors (with `validate` subcommand)

---

### `warden reset`

Clear specific Warden state.

| Aspect | Detail |
| ------ | ------ |
| **Usage** | `warden reset [OPTIONS]` |
| **Preconditions** | Warden is initialized |
| **Side effects** | Deletes specified state files/directories |

**Options** (at least one required):

| Option | Type | Description |
| ------ | ---- | ----------- |
| `--understanding` | flag | Clear understanding docs only |
| `--improvements` | flag | Clear improvement records only |
| `--all` | flag | Clear all state (understanding + improvements + state.db) |

**Output** (stdout):
- Confirmation of what was cleared

**Exit codes**:
- 0: Success
- 1: No option specified, or Warden not initialized

---

## Git Hook Contract

### post-commit hook

Appended to `.git/hooks/post-commit` during `warden init`.

```bash
# Added by Warden
warden analyze 2>/dev/null &
```

**Behavior**:
- Runs in background (trailing `&`)
- Stderr suppressed (`2>/dev/null`)
- Never blocks the developer's commit flow
- If `warden` is not on PATH, silently fails

## Error Output

All errors are written to stderr. Format:

```
Error: <message>
```

Warden does not use stack traces in user-facing output. Verbose/debug logging can be enabled via `WARDEN_DEBUG=1` environment variable (writes to `.warden/debug.log`).
