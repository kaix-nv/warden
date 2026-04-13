# Warden Skills Design Spec

**Convert Warden's knowledge consumption into Claude Code skills**

**Date:** 2026-04-13
**Status:** Approved Design
**Depends on:** Warden MVP + Dependency Graph (implemented)

---

## Overview

Convert Warden's review and ask functionality from standalone CLI commands into Claude Code skills. The CLI remains the knowledge builder (`init`, `analyze`, `status`, `impact`). Skills become the knowledge consumer — running inside Claude Code where developers already work.

### What Changes

- Add `warden impact <files>` CLI command — queries graph + filters understanding docs
- Add 3 Claude Code skills: `warden-review-pr`, `warden-review`, `warden-ask`
- `warden init` now also creates `.claude/skills/warden-*/SKILL.md`
- Remove `warden review-pr` and `warden ask` CLI commands (replaced by skills)

### Why Skills

- **Review to fix loop:** Skill reviews code, finds issues, fixes them — all in one Claude Code session
- **Conversational:** User can ask follow-up questions, disagree, guide the fix
- **No context loss:** Claude Code already has the files open — no subprocess boundary

---

## New CLI Command: `warden impact`

Queries the dependency graph and loads relevant understanding docs for a set of files.

```bash
warden impact path/to/file1.py path/to/file2.py
```

**Output** (printed to stdout, consumed by skills via Bash):

```
## Dependency Impact

### path/to/file1.py
  Contains: ClassName (class, lines 10-50), function_name (function, lines 52-60)
  Downstream dependents:
    - other/module.py imports ClassName
  Dependencies:
    - base.module
  ClassName inherits from: BaseClass

## Relevant Design Context

### design-decisions.md (relevant sections)

## Some Design Decision
Content referencing the changed files...

### patterns.md (relevant sections)

## Some Pattern
Content referencing the changed files...
```

**Implementation:** Combines `GraphManager.get_impact_summary()` + `load_relevant_understanding()` using `GraphManager.get_related_keywords()`. Prints the combined text to stdout.

---

## Skills

All skills live at `.claude/skills/warden-<name>/SKILL.md` in the project repo, created by `warden init`.

### Skill 1: warden-review-pr

**File:** `.claude/skills/warden-review-pr/SKILL.md`

**Triggers:** `/warden-review-pr <number>` or natural language like "review PR #1187"

**Frontmatter:**
```yaml
---
name: warden-review-pr
description: Review a pull request using Warden's accumulated codebase understanding, design decisions, and dependency graph. Use when reviewing PRs or when the user mentions reviewing a PR number.
user-invocable: true
allowed-tools: Read Grep Glob Bash(warden *) Bash(gh *) Bash(git *)
---
```

**Behavior:**
1. Extract PR number from arguments
2. Run `gh pr view <N> --json files -q '.files[].path'` to get changed files
3. Run `warden impact <changed-files>` to get graph context + relevant understanding
4. Run `gh pr diff <N>` to get the full diff
5. Run `gh pr view <N>` to get description and review comments
6. Review for correctness, consistency, design coherence, broken assumptions
7. Reference specific design decisions and patterns from the Warden context
8. Present findings as structured feedback
9. Ask user: "Want me to fix any of these issues?"
10. If yes: create branch, edit files, commit, push, update PR

### Skill 2: warden-review

**File:** `.claude/skills/warden-review/SKILL.md`

**Triggers:** `/warden-review` or natural language like "review my current changes"

**Frontmatter:**
```yaml
---
name: warden-review
description: Review current uncommitted or staged changes using Warden's codebase understanding and dependency graph. Use when reviewing local changes before committing.
user-invocable: true
allowed-tools: Read Grep Glob Bash(warden *) Bash(git *)
---
```

**Behavior:**
1. Run `git diff --name-only` to get changed files
2. Run `warden impact <changed-files>` for context
3. Run `git diff` for the full diff
4. Review changes against design decisions and patterns
5. Present findings
6. If issues found: suggest fixes, edit files directly with user approval

### Skill 3: warden-ask

**File:** `.claude/skills/warden-ask/SKILL.md`

**Triggers:** `/warden-ask "question"` or auto-invoked when question matches codebase context

**Frontmatter:**
```yaml
---
name: warden-ask
description: Answer questions about the codebase using Warden's accumulated understanding of architecture, design decisions, relationships, and patterns. Use when the user asks why code is designed a certain way, what components depend on each other, or how to extend the codebase.
user-invocable: true
allowed-tools: Read Grep Glob Bash(warden *) Bash(git *)
---
```

**Behavior:**
1. Read all `.warden/understanding/*.md` files
2. Answer the question citing specific decisions, commits, and PRs
3. If the question mentions specific files, also run `warden impact <files>` for structural context
4. Follow-up conversation works naturally

---

## `warden init` Changes

After creating `.warden/`, also create skills:

```
.claude/skills/
├── warden-review-pr/SKILL.md
├── warden-review/SKILL.md
└── warden-ask/SKILL.md
```

The skill files are static markdown templates written by Warden's Python code. Users can customize them after creation.

Also add `.claude/skills/` entries to `.gitignore` exclusion — these should be committed so the team shares them.

---

## CLI Changes

**Add:**
- `warden impact <file1> [file2...]` — print graph impact + relevant understanding

**Remove:**
- `warden review-pr` — replaced by skill
- `warden ask` — replaced by skill

**Keep unchanged:**
- `warden init` (+ now creates skills)
- `warden analyze`
- `warden status`
- `warden config`
- `warden reset`

---

## File Changes Summary

```
New files:
  warden/skills/           # Skill template content (Python strings)
    templates.py            # SKILL.md content for all 3 skills

Modified files:
  warden/cli.py            # Add impact command, remove review-pr and ask
  warden/orchestrator.py   # Add impact() method, remove review_pr() and ask()
                            # Add install_skills() called from init()
```
