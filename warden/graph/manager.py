import fnmatch
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event
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
            if self._should_skip(rel, ignore_patterns):
                continue
            parts = rel.split("/")
            module_qn = ".".join(parts)
            # The __init__.py file is parsed as a "file" node with the module's qualified_name.
            # Upgrade that node to type "module" so package nodes appear correctly.
            upgraded = False
            for n in all_nodes:
                if n.qualified_name == module_qn:
                    n.type = "module"
                    upgraded = True
                    break
            if not upgraded:
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

        all_edges = self._resolve_inheritance_edges(all_nodes, all_edges)
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
            # Also load existing nodes from DB for cross-file inheritance resolution
            with Session(self.engine) as session:
                existing = [
                    ParsedNode(type=n.type, name=n.name, qualified_name=n.qualified_name,
                               file_path=n.file_path, line_start=n.line_start,
                               line_end=n.line_end)
                    for n in session.query(GraphNode).all()
                ]
            combined_nodes = existing + all_nodes
            all_edges = self._resolve_inheritance_edges(combined_nodes, all_edges)
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

            result_nodes = [session.get(GraphNode, nid) for nid in dependents]
            return [
                {"id": n.id, "type": n.type, "name": n.name,
                 "qualified_name": n.qualified_name, "file_path": n.file_path}
                for n in result_nodes
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

            result_nodes = [session.get(GraphNode, nid) for nid in deps]
            return [
                {"id": n.id, "type": n.type, "name": n.name,
                 "qualified_name": n.qualified_name, "file_path": n.file_path}
                for n in result_nodes
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

    def get_related_keywords(self, file_paths: list[str]) -> list[str]:
        """Get keywords (names, qualified names) for nodes related to these files."""
        keywords = set()
        for fp in file_paths:
            if not fp.endswith(".py"):
                continue
            # Add the file path and module name as keywords
            keywords.add(fp)
            with Session(self.engine) as session:
                file_nodes = session.query(GraphNode).filter(
                    GraphNode.file_path == fp
                ).all()
                for n in file_nodes:
                    keywords.add(n.name)
                    keywords.add(n.qualified_name)

            # Add dependents and dependencies
            for node_dict in self.get_dependents(fp) + self.get_dependencies(fp):
                keywords.add(node_dict["name"])
                keywords.add(node_dict["qualified_name"])

            # Add inheritance chains for classes in this file
            with Session(self.engine) as session:
                classes = session.query(GraphNode).filter(
                    GraphNode.file_path == fp,
                    GraphNode.type == "class",
                ).all()
                for cls in classes:
                    for a in self.get_ancestors(cls.qualified_name):
                        keywords.add(a["name"])
                    for d in self.get_descendants(cls.qualified_name):
                        keywords.add(d["name"])

        # Filter out very short/generic keywords that would match too broadly
        return [k for k in keywords if len(k) > 2]

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

    def _resolve_inheritance_edges(
        self, nodes: list[ParsedNode], edges: list[ParsedEdge]
    ) -> list[ParsedEdge]:
        """Resolve unqualified base class names in inherits edges to qualified names."""
        # Build lookup: short name → qualified name (prefer same module)
        name_to_qn: dict[str, str] = {}
        for n in nodes:
            if n.type == "class":
                name_to_qn[n.name] = n.qualified_name

        resolved = []
        for edge in edges:
            if edge.type == "inherits":
                target = edge.target_qualified_name
                # If target is unqualified (no dot) or not in nodes, try to resolve
                target_qn = target
                if "." not in target or target not in {n.qualified_name for n in nodes}:
                    resolved_qn = name_to_qn.get(target)
                    if resolved_qn:
                        target_qn = resolved_qn
                resolved.append(ParsedEdge(edge.source_qualified_name, target_qn, edge.type))
            else:
                resolved.append(edge)
        return resolved

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
