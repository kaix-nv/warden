# Dependency Graph Design Spec

**Structured code relationship graph for Warden**

**Date:** 2026-04-12
**Status:** Approved Design
**Depends on:** Warden MVP (implemented)

---

## Overview

Add a structured dependency graph to Warden that maps relationships between modules, files, classes, and functions. Built via Python AST parsing, stored in SQLite alongside existing state. Agents receive relevant subgraph context when reviewing code, enabling them to understand what's affected by a change.

### Core Assumptions

1. **Code is relational** — components have contracts, dependencies, and shared infrastructure. New code must plug into what exists.
2. **Code is evolutionary** — the current structure is the result of decisions and lessons. The graph captures structure; annotations (future) will link structure to history.

### What This Adds

- AST parser that extracts nodes (modules, files, classes, functions) and edges (imports, inheritance, calls, containment)
- SQLite graph storage with three tables (nodes, edges, annotations)
- Graph manager with build, update, and query operations
- Impact summary generation for agent prompts
- Integration with ReviewAgent for context-aware code review

### What This Does NOT Add (Yet)

- Claude Code enrichment of the graph (annotations table exists but is empty)
- Graph context for AskAgent (future — needs entity extraction from free-text questions)
- Cross-language support (Python only)
- Runtime/dynamic relationship detection (static analysis only)

---

## Schema

Three new tables in the existing `state.db`, using the shared SQLAlchemy `Base` from `state.py`.

```sql
graph_nodes (
    id              INTEGER PRIMARY KEY,
    type            TEXT NOT NULL,           -- module | file | class | function
    name            TEXT NOT NULL,           -- short name: "QuantizerConfig"
    qualified_name  TEXT NOT NULL UNIQUE,    -- "modelopt.torch.quantization.QuantizerConfig"
    file_path       TEXT,                    -- relative: "modelopt/torch/quantization/config.py"
    line_start      INTEGER,
    line_end        INTEGER,
    updated_at      DATETIME NOT NULL
)

graph_edges (
    id          INTEGER PRIMARY KEY,
    source_id   INTEGER NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_id   INTEGER NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,               -- imports | inherits | calls | contains
    UNIQUE(source_id, target_id, type)
)

graph_annotations (
    id              INTEGER PRIMARY KEY,
    node_id         INTEGER NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,           -- design_decision | tech_debt | lesson_learned | extension_point | contract
    content         TEXT NOT NULL,
    source_commit   TEXT,
    source_pr       TEXT,
    created_at      DATETIME NOT NULL
)
```

**Edge types:**
- `imports` — file A imports from file B
- `inherits` — class A extends class B
- `calls` — function A calls function B (best-effort, resolved from imports and local scope)
- `contains` — hierarchy: module contains file, file contains class, class contains method

**CASCADE deletes:** When a node is deleted (e.g., file re-parsed), all its edges and annotations are automatically removed.

---

## AST Parser

`warden/graph/parser.py` — walks Python files and extracts nodes + edges.

### What It Extracts

Per `.py` file:
- **File node** (always created)
- **Class nodes** for each `class` definition
- **Function nodes** for each top-level function and method
- **Import edges** from `import X` and `from X import Y` statements
- **Inheritance edges** from `class Foo(Bar)` base classes
- **Call edges** from function/method calls within bodies (best-effort)
- **Contains edges** for the hierarchy: file→class, file→function, class→method

### What It Skips

- Non-Python files
- Files matching config ignore patterns (`*.lock`, `vendor/**`, etc.)
- `__pycache__/`, `.git/`

### Call Resolution Strategy

- **Imports:** Reliable — AST gives exact import paths
- **Inheritance:** Reliable — base class names resolved via imports
- **Calls:** Best-effort — resolved from imports and local scope. Unresolvable calls (dynamic dispatch, computed attribute access) are skipped rather than guessed

### Interface

```python
@dataclass
class ParsedNode:
    type: str           # module | file | class | function
    name: str
    qualified_name: str
    file_path: str
    line_start: int | None
    line_end: int | None

@dataclass
class ParsedEdge:
    source_qualified_name: str
    target_qualified_name: str
    type: str           # imports | inherits | calls | contains

def parse_file(file_path: Path, repo_root: Path) -> tuple[list[ParsedNode], list[ParsedEdge]]
```

Returns nodes and edges with qualified names. The manager resolves qualified names to node IDs when inserting into the DB.

---

## Graph Manager

`warden/graph/manager.py` — owns all graph operations.

### Build (full, during `warden init`)

1. Walk all `.py` files in the repo (respecting ignore patterns from config)
2. Parse each file → nodes + edges
3. Create module nodes for each directory with `__init__.py`
4. Add `contains` edges (module→file, file→class, class→method)
5. Resolve cross-file edges by matching qualified names
6. Write to SQLite

### Update (incremental, during `warden analyze`)

1. Get list of changed files from the commit
2. For each changed file:
   - Delete all nodes where `file_path` = this file (CASCADE deletes edges)
   - Re-parse the file → new nodes + edges
   - Insert new nodes + edges
3. For deleted files: delete their nodes
4. For new files: parse and insert

### Query Methods

```python
class GraphManager:
    def build_full(self, repo_path: Path, ignore_patterns: list[str])
        """Parse entire repo and populate graph."""

    def update_files(self, changed_files: list[str], deleted_files: list[str])
        """Incrementally update graph for changed/deleted files."""

    def get_dependents(self, file_path: str) -> list[dict]
        """What files/classes/functions depend on this file?"""

    def get_dependencies(self, file_path: str) -> list[dict]
        """What does this file depend on?"""

    def get_ancestors(self, qualified_name: str) -> list[dict]
        """Inheritance chain upward."""

    def get_descendants(self, qualified_name: str) -> list[dict]
        """What classes inherit from this?"""

    def get_impact_summary(self, file_paths: list[str]) -> str
        """For a set of changed files, produce a text summary
        of what's affected — formatted for agent prompts."""
```

### Impact Summary Format

Given changed files, `get_impact_summary` returns text like:

```
## Dependency Impact

### quantization/config.py
  Contains: QuantizerConfig (class, lines 45-120)
  Downstream dependents:
    - quantization/quantize.py imports QuantizerConfig
    - export/onnx.py imports QuantizerConfig
    - recipes/loader.py imports QuantizerConfig
  QuantizerConfig inherits from: BaseConfig
  3 classes inherit from QuantizerConfig: INT8Config, FP8Config, MixedConfig
```

---

## Agent Integration

### ReviewAgent.review() — commit review

```
Before: prompt = understanding_docs + diff
After:  prompt = understanding_docs + impact_summary + diff
```

`review()` gains an optional `impact_summary: str` parameter. The orchestrator queries the graph and passes the result.

### ReviewAgent.review_pr() — PR review

```
Before: prompt = understanding_docs + "fetch PR via gh"
After:  prompt = understanding_docs + impact_summary + "fetch PR via gh"
```

The orchestrator fetches the PR file list via `gh pr view --json files`, queries the graph, and passes the impact summary.

### AskAgent — no change for now

Graph context for free-text questions requires entity extraction. Deferred to future work.

---

## Orchestrator Changes

```python
# In __init__:
self.graph_manager = GraphManager(self.warden_dir / "state.db", repo_path)

# In init():
# After bootstrap understanding, build graph
self.graph_manager.build_full(self.repo_path, self.config.git.ignore_patterns)

# In analyze() → _analyze_commit():
# After incremental understand, update graph
changed = self.git_repo.get_commit_files(commit_hash)
self.graph_manager.update_files(changed_files=changed, deleted_files=[])
# Get impact summary for review
impact = self.graph_manager.get_impact_summary(changed)
self.review_agent.review(..., impact_summary=impact)

# In review_pr():
# Orchestrator fetches PR file list via subprocess (not Claude Code)
pr_files = subprocess.run(
    ["gh", "pr", "view", str(pr_number), "--json", "files", "-q", ".files[].path"],
    capture_output=True, text=True, cwd=self.repo_path
).stdout.strip().splitlines()
impact = self.graph_manager.get_impact_summary(pr_files)
self.review_agent.review_pr(pr_number, impact_summary=impact)
```

---

## Project Structure

```
warden/
├── graph/
│   ├── __init__.py
│   ├── parser.py       # AST parsing: file → nodes + edges
│   ├── manager.py      # Build, update, query the graph
│   └── models.py       # SQLAlchemy: GraphNode, GraphEdge, GraphAnnotation
├── agents/
│   ├── review.py       # Modified: accepts impact_summary
│   └── ...
├── orchestrator.py     # Modified: creates GraphManager, wires it in
├── state.py            # Unchanged (graph imports Base from here)
└── ...
```

---

## Technology

- **AST parsing:** Python `ast` module (stdlib, no new dependencies)
- **Storage:** SQLAlchemy + SQLite (existing stack)
- **Recursive queries:** SQLite recursive CTEs for transitive dependency traversal
