# Dependency Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a structured dependency graph to Warden that maps relationships between modules, files, classes, and functions via Python AST parsing, stored in SQLite, with impact summaries fed to ReviewAgent.

**Architecture:** AST parser extracts nodes and edges from Python files. Graph manager stores them in SQLite (same DB as existing state). On review, orchestrator queries the graph for impact summary and injects it into the ReviewAgent prompt. Three new tables (graph_nodes, graph_edges, graph_annotations) share the existing SQLAlchemy Base.

**Tech Stack:** Python `ast` (stdlib), SQLAlchemy 2.0, SQLite, pytest

---

## File Structure

```
warden/
├── graph/
│   ├── __init__.py          # Empty
│   ├── models.py            # SQLAlchemy models: GraphNode, GraphEdge, GraphAnnotation
│   ├── parser.py            # AST parsing: file → ParsedNode + ParsedEdge
│   └── manager.py           # Build, update, query the graph
├── agents/
│   └── review.py            # Modified: review() and review_pr() accept impact_summary
├── orchestrator.py          # Modified: creates GraphManager, wires graph into workflows
└── state.py                 # Unchanged (graph/models.py imports Base from here)

tests/
├── test_graph_models.py     # Schema tests
├── test_graph_parser.py     # AST parsing tests
├── test_graph_manager.py    # Build, update, query tests
├── test_review.py           # Modified: tests for impact_summary in prompts
└── test_orchestrator.py     # Modified: tests for graph integration
```

---

## Task 1: Graph SQLAlchemy Models

**Files:**
- Create: `warden/graph/__init__.py`
- Create: `warden/graph/models.py`
- Create: `tests/test_graph_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_graph_models.py`:
```python
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from warden.state import Base
from warden.graph.models import GraphNode, GraphEdge, GraphAnnotation


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    # Enable foreign key enforcement for CASCADE
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_node(db_session):
    node = GraphNode(
        type="file",
        name="config.py",
        qualified_name="warden.config",
        file_path="warden/config.py",
        line_start=1,
        line_end=50,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(node)
    db_session.commit()
    assert node.id is not None


def test_create_edge(db_session):
    source = GraphNode(type="file", name="cli.py", qualified_name="warden.cli",
                       file_path="warden/cli.py", updated_at=datetime.now(timezone.utc))
    target = GraphNode(type="file", name="config.py", qualified_name="warden.config",
                       file_path="warden/config.py", updated_at=datetime.now(timezone.utc))
    db_session.add_all([source, target])
    db_session.flush()
    edge = GraphEdge(source_id=source.id, target_id=target.id, type="imports")
    db_session.add(edge)
    db_session.commit()
    assert edge.id is not None


def test_create_annotation(db_session):
    node = GraphNode(type="class", name="QuantizerConfig",
                     qualified_name="modelopt.quantization.QuantizerConfig",
                     file_path="modelopt/quantization/config.py",
                     updated_at=datetime.now(timezone.utc))
    db_session.add(node)
    db_session.flush()
    ann = GraphAnnotation(
        node_id=node.id, type="design_decision",
        content="Redesigned in PR #1094", source_pr="1094",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(ann)
    db_session.commit()
    assert ann.id is not None


def test_cascade_delete_removes_edges(db_session):
    source = GraphNode(type="file", name="a.py", qualified_name="a",
                       file_path="a.py", updated_at=datetime.now(timezone.utc))
    target = GraphNode(type="file", name="b.py", qualified_name="b",
                       file_path="b.py", updated_at=datetime.now(timezone.utc))
    db_session.add_all([source, target])
    db_session.flush()
    edge = GraphEdge(source_id=source.id, target_id=target.id, type="imports")
    db_session.add(edge)
    db_session.commit()

    db_session.delete(source)
    db_session.commit()
    assert db_session.query(GraphEdge).count() == 0


def test_cascade_delete_removes_annotations(db_session):
    node = GraphNode(type="class", name="Foo", qualified_name="mod.Foo",
                     file_path="mod.py", updated_at=datetime.now(timezone.utc))
    db_session.add(node)
    db_session.flush()
    ann = GraphAnnotation(node_id=node.id, type="tech_debt", content="needs refactor",
                          created_at=datetime.now(timezone.utc))
    db_session.add(ann)
    db_session.commit()

    db_session.delete(node)
    db_session.commit()
    assert db_session.query(GraphAnnotation).count() == 0


def test_unique_edge_constraint(db_session):
    a = GraphNode(type="file", name="a.py", qualified_name="a",
                  file_path="a.py", updated_at=datetime.now(timezone.utc))
    b = GraphNode(type="file", name="b.py", qualified_name="b",
                  file_path="b.py", updated_at=datetime.now(timezone.utc))
    db_session.add_all([a, b])
    db_session.flush()
    db_session.add(GraphEdge(source_id=a.id, target_id=b.id, type="imports"))
    db_session.commit()
    from sqlalchemy.exc import IntegrityError
    db_session.add(GraphEdge(source_id=a.id, target_id=b.id, type="imports"))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_graph_models.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/graph/__init__.py`:
```python
```

`warden/graph/models.py`:
```python
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from warden.state import Base


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    qualified_name = Column(String, nullable=False, unique=True)
    file_path = Column(String, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=False)

    outgoing_edges = relationship("GraphEdge", foreign_keys="GraphEdge.source_id",
                                  cascade="all, delete-orphan", passive_deletes=True)
    incoming_edges = relationship("GraphEdge", foreign_keys="GraphEdge.target_id",
                                  cascade="all, delete-orphan", passive_deletes=True)
    annotations = relationship("GraphAnnotation", cascade="all, delete-orphan",
                               passive_deletes=True)


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint("source_id", "target_id", "type"),)


class GraphAnnotation(Base):
    __tablename__ = "graph_annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source_commit = Column(String, nullable=True)
    source_pr = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_graph_models.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/graph/__init__.py warden/graph/models.py tests/test_graph_models.py
git commit -m "feat: graph SQLAlchemy models for nodes, edges, annotations"
```

---

## Task 2: AST Parser — Nodes and Containment

**Files:**
- Create: `warden/graph/parser.py`
- Create: `tests/test_graph_parser.py`

This task implements node extraction and `contains` edges. Import/inheritance/call edges are Task 3.

- [ ] **Step 1: Write the failing test**

`tests/test_graph_parser.py`:
```python
from pathlib import Path
from textwrap import dedent

import pytest

from warden.graph.parser import parse_file, ParsedNode, ParsedEdge


@pytest.fixture
def repo(tmp_path):
    """Create a small Python project."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "models.py").write_text(dedent("""\
        class User:
            def __init__(self, name: str):
                self.name = name

            def greet(self) -> str:
                return f"Hello, {self.name}"

        class Admin(User):
            role = "admin"

        def create_user(name: str) -> User:
            return User(name)
    """))
    return tmp_path


def test_parse_extracts_file_node(repo):
    nodes, edges = parse_file(repo / "myapp" / "models.py", repo)
    file_nodes = [n for n in nodes if n.type == "file"]
    assert len(file_nodes) == 1
    assert file_nodes[0].name == "models.py"
    assert file_nodes[0].qualified_name == "myapp.models"
    assert file_nodes[0].file_path == "myapp/models.py"


def test_parse_extracts_class_nodes(repo):
    nodes, edges = parse_file(repo / "myapp" / "models.py", repo)
    class_nodes = [n for n in nodes if n.type == "class"]
    names = {n.name for n in class_nodes}
    assert names == {"User", "Admin"}
    user = next(n for n in class_nodes if n.name == "User")
    assert user.qualified_name == "myapp.models.User"
    assert user.line_start is not None


def test_parse_extracts_function_nodes(repo):
    nodes, edges = parse_file(repo / "myapp" / "models.py", repo)
    func_nodes = [n for n in nodes if n.type == "function"]
    names = {n.name for n in func_nodes}
    assert "create_user" in names
    assert "__init__" in names
    assert "greet" in names


def test_parse_extracts_contains_edges(repo):
    nodes, edges = parse_file(repo / "myapp" / "models.py", repo)
    contains = [e for e in edges if e.type == "contains"]
    # file contains User, Admin, create_user
    file_contains = [e for e in contains if e.source_qualified_name == "myapp.models"]
    targets = {e.target_qualified_name for e in file_contains}
    assert "myapp.models.User" in targets
    assert "myapp.models.Admin" in targets
    assert "myapp.models.create_user" in targets


def test_parse_extracts_method_contains(repo):
    nodes, edges = parse_file(repo / "myapp" / "models.py", repo)
    contains = [e for e in edges if e.type == "contains"]
    # User contains __init__, greet
    user_contains = [e for e in contains if e.source_qualified_name == "myapp.models.User"]
    targets = {e.target_qualified_name for e in user_contains}
    assert "myapp.models.User.__init__" in targets
    assert "myapp.models.User.greet" in targets


def test_parse_handles_empty_file(repo):
    nodes, edges = parse_file(repo / "myapp" / "__init__.py", repo)
    assert len(nodes) == 1  # just the file node
    assert nodes[0].type == "file"


def test_parse_handles_syntax_error(repo):
    (repo / "myapp" / "broken.py").write_text("def foo(:\n  pass\n")
    nodes, edges = parse_file(repo / "myapp" / "broken.py", repo)
    # Should return file node only, no crash
    assert len(nodes) == 1
    assert nodes[0].type == "file"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_graph_parser.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/graph/parser.py`:
```python
import ast
from dataclasses import dataclass
from pathlib import Path


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


def _file_to_module(file_path: Path, repo_root: Path) -> str:
    """Convert file path to Python module qualified name."""
    rel = file_path.relative_to(repo_root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def parse_file(file_path: Path, repo_root: Path) -> tuple[list[ParsedNode], list[ParsedEdge]]:
    """Parse a Python file and extract nodes + edges."""
    rel_path = str(file_path.relative_to(repo_root))
    module_name = _file_to_module(file_path, repo_root)

    file_node = ParsedNode(
        type="file",
        name=file_path.name,
        qualified_name=module_name,
        file_path=rel_path,
        line_start=1,
        line_end=None,
    )
    nodes = [file_node]
    edges = []

    source = file_path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return nodes, edges

    file_node.line_end = len(source.splitlines())

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_qn = f"{module_name}.{node.name}"
            nodes.append(ParsedNode(
                type="class", name=node.name, qualified_name=class_qn,
                file_path=rel_path, line_start=node.lineno, line_end=node.end_lineno,
            ))
            edges.append(ParsedEdge(module_name, class_qn, "contains"))

            # Extract methods
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_qn = f"{class_qn}.{item.name}"
                    nodes.append(ParsedNode(
                        type="function", name=item.name, qualified_name=method_qn,
                        file_path=rel_path, line_start=item.lineno, line_end=item.end_lineno,
                    ))
                    edges.append(ParsedEdge(class_qn, method_qn, "contains"))

            # Extract inheritance edges
            for base in node.bases:
                base_name = _resolve_base_name(base)
                if base_name:
                    edges.append(ParsedEdge(class_qn, base_name, "inherits"))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_qn = f"{module_name}.{node.name}"
            nodes.append(ParsedNode(
                type="function", name=node.name, qualified_name=func_qn,
                file_path=rel_path, line_start=node.lineno, line_end=node.end_lineno,
            ))
            edges.append(ParsedEdge(module_name, func_qn, "contains"))

    # Extract import edges
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(ParsedEdge(module_name, alias.name, "imports"))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                edges.append(ParsedEdge(module_name, node.module, "imports"))

    return nodes, edges


def _resolve_base_name(base: ast.expr) -> str | None:
    """Extract a dotted name from a base class expression."""
    if isinstance(base, ast.Name):
        return base.id
    elif isinstance(base, ast.Attribute):
        parts = []
        current = base
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_graph_parser.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/graph/parser.py tests/test_graph_parser.py
git commit -m "feat: AST parser extracting nodes, containment, imports, inheritance"
```

---

## Task 3: Graph Manager — Build and Update

**Files:**
- Create: `warden/graph/manager.py`
- Create: `tests/test_graph_manager.py`

- [ ] **Step 1: Write the failing test**

`tests/test_graph_manager.py`:
```python
from pathlib import Path
from textwrap import dedent

import pytest

from warden.graph.manager import GraphManager


@pytest.fixture
def project(tmp_path):
    """Create a Python project with dependencies."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    (pkg / "models.py").write_text(dedent("""\
        class BaseModel:
            pass

        class User(BaseModel):
            name: str

        class Admin(User):
            role: str
    """))

    (pkg / "service.py").write_text(dedent("""\
        from myapp.models import User, Admin

        def get_user(user_id: int) -> User:
            return User()

        def get_admin() -> Admin:
            return Admin()
    """))

    (pkg / "api.py").write_text(dedent("""\
        from myapp.service import get_user

        def handle_request(uid: int):
            return get_user(uid)
    """))

    return tmp_path


@pytest.fixture
def graph(project, tmp_path):
    db_path = tmp_path / "test.db"
    mgr = GraphManager(db_path, project)
    mgr.build_full(project, ignore_patterns=[])
    return mgr


def test_build_creates_nodes(graph):
    nodes = graph.get_all_nodes()
    names = {n["qualified_name"] for n in nodes}
    assert "myapp.models" in names
    assert "myapp.service" in names
    assert "myapp.models.User" in names
    assert "myapp.models.Admin" in names
    assert "myapp.service.get_user" in names


def test_build_creates_module_nodes(graph):
    nodes = graph.get_all_nodes()
    modules = [n for n in nodes if n["type"] == "module"]
    names = {n["qualified_name"] for n in modules}
    assert "myapp" in names


def test_build_creates_import_edges(graph):
    deps = graph.get_dependencies("myapp/service.py")
    dep_names = {d["qualified_name"] for d in deps}
    assert "myapp.models" in dep_names


def test_build_creates_inheritance_edges(graph):
    ancestors = graph.get_ancestors("myapp.models.Admin")
    ancestor_names = {a["qualified_name"] for a in ancestors}
    assert "User" in ancestor_names or "myapp.models.User" in ancestor_names


def test_build_creates_contains_edges(graph):
    deps = graph.get_dependents("myapp/models.py")
    # service.py and api.py depend on models (directly or transitively)
    dep_paths = {d["file_path"] for d in deps if d.get("file_path")}
    assert "myapp/service.py" in dep_paths


def test_get_dependents(graph):
    """What depends on models.py?"""
    deps = graph.get_dependents("myapp/models.py")
    dep_paths = {d["file_path"] for d in deps if d.get("file_path")}
    assert "myapp/service.py" in dep_paths


def test_get_dependencies(graph):
    """What does service.py depend on?"""
    deps = graph.get_dependencies("myapp/service.py")
    dep_names = {d["qualified_name"] for d in deps}
    assert "myapp.models" in dep_names


def test_get_descendants(graph):
    """What inherits from BaseModel?"""
    desc = graph.get_descendants("myapp.models.BaseModel")
    desc_names = {d["qualified_name"] for d in desc}
    assert "myapp.models.User" in desc_names


def test_update_files_incremental(project, graph):
    """Changing a file re-parses it without losing other nodes."""
    # Modify service.py
    (project / "myapp" / "service.py").write_text(
        "from myapp.models import User\n\n"
        "def get_user_v2(uid: int) -> User:\n"
        "    return User()\n"
    )
    graph.update_files(changed_files=["myapp/service.py"], deleted_files=[])

    nodes = graph.get_all_nodes()
    names = {n["qualified_name"] for n in nodes}
    assert "myapp.service.get_user_v2" in names
    assert "myapp.service.get_user" not in names
    # Other nodes still exist
    assert "myapp.models.User" in names


def test_update_files_deleted(project, graph):
    """Deleting a file removes its nodes."""
    (project / "myapp" / "api.py").unlink()
    graph.update_files(changed_files=[], deleted_files=["myapp/api.py"])

    nodes = graph.get_all_nodes()
    names = {n["qualified_name"] for n in nodes}
    assert "myapp.api" not in names
    # Other nodes still exist
    assert "myapp.models" in names


def test_get_impact_summary(graph):
    """Impact summary produces readable text."""
    summary = graph.get_impact_summary(["myapp/models.py"])
    assert "models.py" in summary
    assert "service.py" in summary or "dependents" in summary.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_graph_manager.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/graph/manager.py`:
```python
import fnmatch
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from warden.graph.models import GraphAnnotation, GraphEdge, GraphNode
from warden.graph.parser import ParsedEdge, ParsedNode, parse_file
from warden.state import Base


class GraphManager:
    def __init__(self, db_path: Path, repo_path: Path):
        self.db_path = db_path
        self.repo_path = repo_path
        self.engine = create_engine(f"sqlite:///{db_path}")

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)

    def build_full(self, repo_path: Path, ignore_patterns: list[str]):
        """Parse entire repo and populate graph."""
        # Clear existing graph
        with Session(self.engine) as session:
            session.query(GraphEdge).delete()
            session.query(GraphAnnotation).delete()
            session.query(GraphNode).delete()
            session.commit()

        all_nodes: list[ParsedNode] = []
        all_edges: list[ParsedEdge] = []

        # Find all .py files
        for py_file in repo_path.rglob("*.py"):
            rel = str(py_file.relative_to(repo_path))
            if self._should_skip(rel, ignore_patterns):
                continue
            nodes, edges = parse_file(py_file, repo_path)
            all_nodes.extend(nodes)
            all_edges.extend(edges)

        # Create module nodes for directories with __init__.py
        for init_file in repo_path.rglob("__init__.py"):
            dir_path = init_file.parent
            rel = str(dir_path.relative_to(repo_path))
            parts = rel.split("/")
            module_qn = ".".join(parts)
            if not any(n.qualified_name == module_qn and n.type == "module" for n in all_nodes):
                all_nodes.append(ParsedNode(
                    type="module", name=parts[-1], qualified_name=module_qn,
                    file_path=rel, line_start=None, line_end=None,
                ))
            # Add contains edge: module → file for each .py in this dir
            for py_file in dir_path.glob("*.py"):
                file_qn = ".".join(
                    py_file.relative_to(repo_path).with_suffix("").parts
                )
                if py_file.name == "__init__.py":
                    continue  # __init__.py IS the module node
                all_edges.append(ParsedEdge(module_qn, file_qn, "contains"))

        self._insert_nodes_and_edges(all_nodes, all_edges)

    def update_files(self, changed_files: list[str], deleted_files: list[str]):
        """Incrementally update graph for changed/deleted files."""
        with Session(self.engine) as session:
            # Delete nodes for changed and deleted files
            for file_path in changed_files + deleted_files:
                nodes = session.query(GraphNode).filter(
                    GraphNode.file_path == file_path
                ).all()
                for node in nodes:
                    session.delete(node)
            session.commit()

        # Re-parse changed files
        all_nodes: list[ParsedNode] = []
        all_edges: list[ParsedEdge] = []
        for file_path in changed_files:
            full_path = self.repo_path / file_path
            if full_path.exists():
                nodes, edges = parse_file(full_path, self.repo_path)
                all_nodes.extend(nodes)
                all_edges.extend(edges)

        if all_nodes:
            self._insert_nodes_and_edges(all_nodes, all_edges)

    def get_all_nodes(self) -> list[dict]:
        with Session(self.engine) as session:
            return [
                {"id": n.id, "type": n.type, "name": n.name,
                 "qualified_name": n.qualified_name, "file_path": n.file_path,
                 "line_start": n.line_start, "line_end": n.line_end}
                for n in session.query(GraphNode).all()
            ]

    def get_dependents(self, file_path: str) -> list[dict]:
        """What files/classes depend on this file? (reverse imports)"""
        with Session(self.engine) as session:
            # Find all nodes in this file
            file_nodes = session.query(GraphNode).filter(
                GraphNode.file_path == file_path
            ).all()
            file_node_ids = {n.id for n in file_nodes}
            file_qnames = {n.qualified_name for n in file_nodes}

            # Find edges pointing TO these nodes (imports, inherits)
            dependents = set()
            edges = session.query(GraphEdge).filter(
                GraphEdge.target_id.in_(file_node_ids),
                GraphEdge.type.in_(["imports", "inherits"]),
            ).all()
            for edge in edges:
                source = session.get(GraphNode, edge.source_id)
                if source:
                    dependents.add(source.id)

            # Also find edges where target qualified_name matches
            # (for unresolved cross-file references)
            all_import_edges = session.query(GraphEdge).filter(
                GraphEdge.type == "imports"
            ).all()
            for edge in all_import_edges:
                target = session.get(GraphNode, edge.target_id)
                if target and target.qualified_name in file_qnames:
                    source = session.get(GraphNode, edge.source_id)
                    if source:
                        dependents.add(source.id)

            return [
                {"id": n.id, "type": n.type, "name": n.name,
                 "qualified_name": n.qualified_name, "file_path": n.file_path}
                for n in [session.get(GraphNode, nid) for nid in dependents]
                if n is not None
            ]

    def get_dependencies(self, file_path: str) -> list[dict]:
        """What does this file depend on? (forward imports)"""
        with Session(self.engine) as session:
            file_nodes = session.query(GraphNode).filter(
                GraphNode.file_path == file_path
            ).all()
            file_node_ids = {n.id for n in file_nodes}

            deps = set()
            edges = session.query(GraphEdge).filter(
                GraphEdge.source_id.in_(file_node_ids),
                GraphEdge.type.in_(["imports", "inherits"]),
            ).all()
            for edge in edges:
                target = session.get(GraphNode, edge.target_id)
                if target:
                    deps.add(target.id)

            return [
                {"id": n.id, "type": n.type, "name": n.name,
                 "qualified_name": n.qualified_name, "file_path": n.file_path}
                for n in [session.get(GraphNode, nid) for nid in deps]
                if n is not None
            ]

    def get_ancestors(self, qualified_name: str) -> list[dict]:
        """Inheritance chain upward."""
        with Session(self.engine) as session:
            node = session.query(GraphNode).filter(
                GraphNode.qualified_name == qualified_name
            ).first()
            if not node:
                return []

            ancestors = []
            visited = set()
            queue = [node.id]
            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)
                edges = session.query(GraphEdge).filter(
                    GraphEdge.source_id == current_id,
                    GraphEdge.type == "inherits",
                ).all()
                for edge in edges:
                    parent = session.get(GraphNode, edge.target_id)
                    if parent and parent.id not in visited:
                        ancestors.append({
                            "id": parent.id, "type": parent.type,
                            "name": parent.name, "qualified_name": parent.qualified_name,
                            "file_path": parent.file_path,
                        })
                        queue.append(parent.id)
            return ancestors

    def get_descendants(self, qualified_name: str) -> list[dict]:
        """What classes inherit from this?"""
        with Session(self.engine) as session:
            node = session.query(GraphNode).filter(
                GraphNode.qualified_name == qualified_name
            ).first()
            if not node:
                return []

            descendants = []
            visited = set()
            queue = [node.id]
            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)
                edges = session.query(GraphEdge).filter(
                    GraphEdge.target_id == current_id,
                    GraphEdge.type == "inherits",
                ).all()
                for edge in edges:
                    child = session.get(GraphNode, edge.source_id)
                    if child and child.id not in visited:
                        descendants.append({
                            "id": child.id, "type": child.type,
                            "name": child.name, "qualified_name": child.qualified_name,
                            "file_path": child.file_path,
                        })
                        queue.append(child.id)
            return descendants

    def get_impact_summary(self, file_paths: list[str]) -> str:
        """Produce a text summary of what's affected by changes to these files."""
        lines = ["## Dependency Impact\n"]

        for fp in file_paths:
            if not fp.endswith(".py"):
                continue

            lines.append(f"### {fp}")

            # What's in this file
            with Session(self.engine) as session:
                file_nodes = session.query(GraphNode).filter(
                    GraphNode.file_path == fp,
                    GraphNode.type.in_(["class", "function"]),
                ).all()
                if file_nodes:
                    lines.append("  Contains:")
                    for n in file_nodes:
                        loc = f", lines {n.line_start}-{n.line_end}" if n.line_start else ""
                        lines.append(f"    - {n.name} ({n.type}{loc})")

            # What depends on this file
            dependents = self.get_dependents(fp)
            if dependents:
                lines.append("  Downstream dependents:")
                for d in dependents:
                    path_info = f" ({d['file_path']})" if d.get("file_path") else ""
                    lines.append(f"    - {d['qualified_name']}{path_info}")

            # What this file depends on
            dependencies = self.get_dependencies(fp)
            if dependencies:
                lines.append("  Dependencies:")
                for d in dependencies:
                    lines.append(f"    - {d['qualified_name']}")

            # Inheritance for classes in this file
            with Session(self.engine) as session:
                classes = session.query(GraphNode).filter(
                    GraphNode.file_path == fp,
                    GraphNode.type == "class",
                ).all()
                for cls in classes:
                    ancestors = self.get_ancestors(cls.qualified_name)
                    if ancestors:
                        names = ", ".join(a["name"] for a in ancestors)
                        lines.append(f"  {cls.name} inherits from: {names}")
                    desc = self.get_descendants(cls.qualified_name)
                    if desc:
                        names = ", ".join(d["name"] for d in desc)
                        lines.append(f"  {len(desc)} classes inherit from {cls.name}: {names}")

            lines.append("")

        return "\n".join(lines)

    def _insert_nodes_and_edges(self, nodes: list[ParsedNode], edges: list[ParsedEdge]):
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            # Insert nodes, skip duplicates
            node_map = {}  # qualified_name → id
            # First load existing nodes
            for existing in session.query(GraphNode).all():
                node_map[existing.qualified_name] = existing.id

            for pn in nodes:
                if pn.qualified_name in node_map:
                    continue
                db_node = GraphNode(
                    type=pn.type, name=pn.name, qualified_name=pn.qualified_name,
                    file_path=pn.file_path, line_start=pn.line_start,
                    line_end=pn.line_end, updated_at=now,
                )
                session.add(db_node)
                session.flush()
                node_map[pn.qualified_name] = db_node.id

            # Insert edges, skip if either end is missing
            for pe in edges:
                src_id = node_map.get(pe.source_qualified_name)
                tgt_id = node_map.get(pe.target_qualified_name)
                if src_id and tgt_id:
                    existing = session.query(GraphEdge).filter(
                        GraphEdge.source_id == src_id,
                        GraphEdge.target_id == tgt_id,
                        GraphEdge.type == pe.type,
                    ).first()
                    if not existing:
                        session.add(GraphEdge(
                            source_id=src_id, target_id=tgt_id, type=pe.type,
                        ))

            session.commit()

    def _should_skip(self, rel_path: str, ignore_patterns: list[str]) -> bool:
        if "__pycache__" in rel_path or ".git" in rel_path:
            return True
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_graph_manager.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/graph/manager.py tests/test_graph_manager.py
git commit -m "feat: graph manager with build, update, and query operations"
```

---

## Task 4: Integrate Graph with ReviewAgent

**Files:**
- Modify: `warden/agents/review.py`
- Modify: `tests/test_review.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_review.py`:
```python
def test_review_includes_impact_summary(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."
    impact = "## Dependency Impact\n### config.py\n  Downstream: cli.py imports config"
    agent.review("abc123", "diff", ["config.py"], impact_summary=impact)
    prompt = mock_runner.run.call_args[0][0]
    assert "Dependency Impact" in prompt
    assert "cli.py imports config" in prompt


def test_review_works_without_impact_summary(mock_runner, warden_dir):
    """Existing behavior preserved when no impact_summary."""
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."
    agent.review("abc123", "diff", ["file.py"])
    prompt = mock_runner.run.call_args[0][0]
    assert "correctness" in prompt.lower()


def test_review_pr_includes_impact_summary(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "Looks good."
    impact = "## Dependency Impact\n### models.py\n  3 classes inherit from Base"
    agent.review_pr(42, impact_summary=impact)
    prompt = mock_runner.run.call_args[0][0]
    assert "Dependency Impact" in prompt
    assert "3 classes inherit from Base" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_review.py::test_review_includes_impact_summary -v`
Expected: FAIL (review() doesn't accept impact_summary yet)

- [ ] **Step 3: Modify ReviewAgent**

In `warden/agents/review.py`, update `review()` signature to add `impact_summary: str = ""` and inject it into the prompt. Update `review_pr()` similarly.

`warden/agents/review.py` (full replacement):
```python
from pathlib import Path
from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner


class ReviewAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def review(self, commit_hash: str, diff: str, changed_files: list[str],
               branch_prefix: str = "warden/", impact_summary: str = "") -> str:
        understanding = load_understanding(self.understanding_dir)
        prompt = (
            "You are reviewing a code change as a senior engineer who deeply "
            "understands this codebase's history, design decisions, and patterns.\n\n"
        )
        if understanding:
            prompt += f"Here is your accumulated understanding of this codebase:\n\n{understanding}\n\n---\n\n"
        if impact_summary:
            prompt += f"{impact_summary}\n\n---\n\n"
        prompt += (
            f"Commit: {commit_hash}\n"
            f"Changed files: {', '.join(changed_files)}\n\n"
            f"Diff:\n```\n{diff}\n```\n\n"
            "Review this change for:\n"
            "- **Correctness** — logic errors, edge cases, off-by-ones, race conditions\n"
            "- **Consistency** — does this follow the patterns established elsewhere?\n"
            "- **Design coherence** — does this contradict an established design decision?\n"
            "- **Assumptions** — does this break assumptions other code depends on?\n\n"
            "If you find issues you are confident about:\n"
            f"1. Create a new branch with prefix `{branch_prefix}`\n"
            "2. Apply the fix\n3. Commit the fix\n4. Push the branch\n"
            "5. Create a draft pull request explaining the issue and fix\n\n"
            "If no issues found, say so. Only report issues you are confident about. "
            "This is not a linter — focus on what matters."
        )
        return self.runner.run(prompt)

    def review_pr(self, pr_number: int, impact_summary: str = "") -> str:
        understanding = load_understanding(self.understanding_dir)

        prompt = (
            "You are reviewing a pull request as a senior engineer who deeply "
            "understands this codebase's history, design decisions, and patterns.\n\n"
        )

        if understanding:
            prompt += (
                "Here is your accumulated understanding of this codebase:\n\n"
                f"{understanding}\n\n---\n\n"
            )

        if impact_summary:
            prompt += f"{impact_summary}\n\n---\n\n"

        prompt += (
            f"Fetch PR #{pr_number} using `gh pr view {pr_number}` and "
            f"`gh pr diff {pr_number}` to get the full description, review "
            "comments, and diff.\n\n"
            "Review this PR for:\n"
            "- **Correctness** — logic errors, edge cases, off-by-ones, race conditions\n"
            "- **Consistency** — does this follow the patterns established in this codebase?\n"
            "- **Design coherence** — does this contradict an established design decision?\n"
            "- **Assumptions** — does this break assumptions other code depends on?\n\n"
            "Reference specific design decisions, architecture choices, or patterns "
            "from the understanding docs when they are relevant to your review.\n\n"
            "Provide your review as structured feedback. For each issue:\n"
            "- File and line range\n"
            "- What the issue is\n"
            "- Why it matters (cite the relevant design decision or pattern)\n"
            "- Suggested fix\n\n"
            "If the PR looks good, say so and explain why it aligns well with "
            "the codebase's design. Only flag issues you are confident about."
        )

        return self.runner.run(prompt)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_review.py -v`
Expected: All 12 tests PASS (9 existing + 3 new)

- [ ] **Step 5: Commit**

```bash
git add warden/agents/review.py tests/test_review.py
git commit -m "feat: ReviewAgent accepts impact_summary from dependency graph"
```

---

## Task 5: Integrate Graph with Orchestrator

**Files:**
- Modify: `warden/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_orchestrator.py`:
```python
def test_init_builds_graph(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    # Add a Python file so the graph has something to parse
    (repo_path / "app.py").write_text("import os\n\ndef main(): pass\n")
    repo.index.add(["app.py"])
    repo.index.commit("Add app")
    orchestrator.init()
    nodes = orchestrator.graph_manager.get_all_nodes()
    assert len(nodes) > 0


def test_analyze_updates_graph(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    _remove_hook(repo_path)
    mock_runner.run.reset_mock()

    (repo_path / "new_module.py").write_text("class Foo:\n    pass\n")
    repo.index.add(["new_module.py"])
    repo.index.commit("Add new module")

    orchestrator.analyze()
    nodes = orchestrator.graph_manager.get_all_nodes()
    names = {n["qualified_name"] for n in nodes}
    assert "new_module.Foo" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_orchestrator.py::test_init_builds_graph -v`
Expected: FAIL (orchestrator doesn't have graph_manager yet)

- [ ] **Step 3: Modify Orchestrator**

In `warden/orchestrator.py`, add:
- Import `GraphManager`
- Create `self.graph_manager` in `__init__`
- Call `graph_manager.build_full()` in `init()` after bootstrap
- Call `graph_manager.update_files()` in `_analyze_commit()` after understand
- Get impact summary and pass to `review_agent.review()` and `review_pr()`

`warden/orchestrator.py` (full replacement):
```python
import subprocess
from pathlib import Path

from warden.agents.ask import AskAgent
from warden.agents.review import ReviewAgent
from warden.agents.runner import AgentRunner
from warden.agents.understand import UnderstandAgent
from warden.config import WardenConfig, load_config
from warden.git.hooks import install_post_commit_hook
from warden.git.repo import GitRepo
from warden.graph.manager import GraphManager
from warden.state import StateManager

GITIGNORE_ENTRY = ".warden/state.db"


class Orchestrator:
    def __init__(self, repo_path: Path, config: WardenConfig | None = None):
        self.repo_path = repo_path
        self.warden_dir = repo_path / ".warden"
        self.config = config or load_config(self.warden_dir / "config.yml")
        self.git_repo = GitRepo(repo_path)

        runner = AgentRunner(cwd=repo_path)
        self.understand_agent = UnderstandAgent(runner, self.warden_dir)
        self.review_agent = ReviewAgent(runner, self.warden_dir)
        self.ask_agent = AskAgent(runner, self.warden_dir)

        self.state = StateManager(self.warden_dir / "state.db")
        self.graph_manager = GraphManager(self.warden_dir / "state.db", repo_path)

    def init(self, pr_count: int | None = None, commit_count: int | None = None):
        """Initialize Warden in the repo."""
        (self.warden_dir / "understanding").mkdir(parents=True, exist_ok=True)
        (self.warden_dir / "improvements" / "pending").mkdir(parents=True, exist_ok=True)
        (self.warden_dir / "improvements" / "history").mkdir(parents=True, exist_ok=True)

        config_path = self.warden_dir / "config.yml"
        if not config_path.exists():
            config_path.write_text(self.config.to_yaml())

        self.state.initialize()
        install_post_commit_hook(self.repo_path)
        self._add_to_gitignore(GITIGNORE_ENTRY)

        effective_pr_count = pr_count or self.config.understanding.bootstrap.pr_count
        effective_commit_count = commit_count or self.config.understanding.bootstrap.commit_count
        self.understand_agent.bootstrap(pr_count=effective_pr_count, commit_count=effective_commit_count)

        # Build dependency graph
        self.graph_manager.build_full(self.repo_path, self.config.git.ignore_patterns)

        for commit in self.git_repo.get_all_commits():
            self.state.record_commit(hash=commit["hash"], timestamp=commit["timestamp"], files_changed=commit["files"])
            self.state.mark_commit_understood(commit["hash"])

    def analyze(self, commit_hash: str | None = None):
        """Analyze new commits since last run."""
        self.state.initialize()
        if commit_hash:
            self._analyze_commit(commit_hash)
            return
        last_hash = self.state.get_last_processed_hash()
        if last_hash:
            commits = self.git_repo.get_commits_since(last_hash)
        else:
            commits = self.git_repo.get_all_commits()
        for commit in reversed(commits):
            self._analyze_commit(commit["hash"])

    def review_pr(self, pr_number: int) -> str:
        """Review a PR using accumulated understanding and dependency graph."""
        # Fetch PR file list
        pr_files = self._get_pr_files(pr_number)
        impact = self.graph_manager.get_impact_summary(pr_files) if pr_files else ""
        return self.review_agent.review_pr(pr_number, impact_summary=impact)

    def ask(self, question: str) -> str:
        return self.ask_agent.ask(question)

    def status(self) -> dict:
        self.state.initialize()
        stats = self.state.get_stats()
        understanding_dir = self.warden_dir / "understanding"
        doc_sizes = {}
        if understanding_dir.exists():
            for doc in understanding_dir.iterdir():
                if doc.suffix == ".md":
                    doc_sizes[doc.name] = doc.stat().st_size
        stats["understanding_docs"] = doc_sizes
        stats["graph_nodes"] = len(self.graph_manager.get_all_nodes())
        return stats

    def _analyze_commit(self, commit_hash: str):
        existing = self.state.get_commit(commit_hash)
        if existing and existing["understand_done"]:
            return
        diff = self.git_repo.get_commit_diff(commit_hash)
        files = self.git_repo.get_commit_files(commit_hash)
        commit_obj = self.git_repo.repo.commit(commit_hash)
        message = commit_obj.message.strip()
        commit_info = {"hash": commit_hash, "message": message, "diff": diff}
        if not existing:
            self.state.record_commit(hash=commit_hash, timestamp=commit_obj.committed_datetime, files_changed=files)
        self.understand_agent.incremental(commit_info)
        self.state.mark_commit_understood(commit_hash)

        # Update graph incrementally
        py_files = [f for f in files if f.endswith(".py")]
        if py_files:
            self.graph_manager.update_files(changed_files=py_files, deleted_files=[])

        if self.config.review.enabled:
            impact = self.graph_manager.get_impact_summary(py_files) if py_files else ""
            self.review_agent.review(
                commit_hash=commit_hash, diff=diff, changed_files=files,
                branch_prefix=self.config.git.branch_prefix, impact_summary=impact,
            )
            self.state.mark_commit_reviewed(commit_hash)

    def _get_pr_files(self, pr_number: int) -> list[str]:
        """Fetch changed file paths from a PR via gh CLI."""
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "files", "-q", ".files[].path"],
            capture_output=True, text=True, cwd=self.repo_path,
        )
        if result.returncode != 0:
            return []
        return [f for f in result.stdout.strip().splitlines() if f]

    def _add_to_gitignore(self, entry: str):
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if entry in content:
                return
            gitignore_path.write_text(content.rstrip() + "\n" + entry + "\n")
        else:
            gitignore_path.write_text(entry + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_orchestrator.py -v`
Expected: All 11 tests PASS (9 existing + 2 new)

- [ ] **Step 5: Run full test suite**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add warden/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: integrate dependency graph into orchestrator workflows"
```

---

## Task 6: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Verify graph builds on a real repo**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && python -c "
from pathlib import Path
from warden.graph.manager import GraphManager
gm = GraphManager(Path('/tmp/test_graph.db'), Path('.'))
gm.build_full(Path('.'), ['*.lock', 'node_modules/**'])
nodes = gm.get_all_nodes()
print(f'Nodes: {len(nodes)}')
for n in nodes[:10]:
    print(f'  {n[\"type\"]:8s} {n[\"qualified_name\"]}')
print(f'...')
summary = gm.get_impact_summary(['warden/orchestrator.py'])
print(summary)
"`
Expected: Shows nodes from the warden codebase and impact summary for orchestrator.py

- [ ] **Step 3: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: final verification of dependency graph feature"
```
