import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedNode:
    type: str
    name: str
    qualified_name: str
    file_path: str
    line_start: int | None
    line_end: int | None


@dataclass
class ParsedEdge:
    source_qualified_name: str
    target_qualified_name: str
    type: str


def _file_to_module(file_path: Path, repo_root: Path) -> str:
    rel = file_path.relative_to(repo_root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def parse_file(file_path: Path, repo_root: Path) -> tuple[list[ParsedNode], list[ParsedEdge]]:
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
                type="class",
                name=node.name,
                qualified_name=class_qn,
                file_path=rel_path,
                line_start=node.lineno,
                line_end=node.end_lineno,
            ))
            edges.append(ParsedEdge(module_name, class_qn, "contains"))
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_qn = f"{class_qn}.{item.name}"
                    nodes.append(ParsedNode(
                        type="function",
                        name=item.name,
                        qualified_name=method_qn,
                        file_path=rel_path,
                        line_start=item.lineno,
                        line_end=item.end_lineno,
                    ))
                    edges.append(ParsedEdge(class_qn, method_qn, "contains"))
            for base in node.bases:
                base_name = _resolve_base_name(base)
                if base_name:
                    edges.append(ParsedEdge(class_qn, base_name, "inherits"))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_qn = f"{module_name}.{node.name}"
            nodes.append(ParsedNode(
                type="function",
                name=node.name,
                qualified_name=func_qn,
                file_path=rel_path,
                line_start=node.lineno,
                line_end=node.end_lineno,
            ))
            edges.append(ParsedEdge(module_name, func_qn, "contains"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(ParsedEdge(module_name, alias.name, "imports"))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                edges.append(ParsedEdge(module_name, node.module, "imports"))

    return nodes, edges


def _resolve_base_name(base: ast.expr) -> str | None:
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
