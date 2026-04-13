from pathlib import Path
from textwrap import dedent
import pytest
from warden.graph.parser import parse_file, ParsedNode, ParsedEdge

@pytest.fixture
def repo(tmp_path):
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
    file_contains = [e for e in contains if e.source_qualified_name == "myapp.models"]
    targets = {e.target_qualified_name for e in file_contains}
    assert "myapp.models.User" in targets
    assert "myapp.models.Admin" in targets
    assert "myapp.models.create_user" in targets

def test_parse_extracts_method_contains(repo):
    nodes, edges = parse_file(repo / "myapp" / "models.py", repo)
    contains = [e for e in edges if e.type == "contains"]
    user_contains = [e for e in contains if e.source_qualified_name == "myapp.models.User"]
    targets = {e.target_qualified_name for e in user_contains}
    assert "myapp.models.User.__init__" in targets
    assert "myapp.models.User.greet" in targets

def test_parse_handles_empty_file(repo):
    nodes, edges = parse_file(repo / "myapp" / "__init__.py", repo)
    assert len(nodes) == 1
    assert nodes[0].type == "file"

def test_parse_handles_syntax_error(repo):
    (repo / "myapp" / "broken.py").write_text("def foo(:\n  pass\n")
    nodes, edges = parse_file(repo / "myapp" / "broken.py", repo)
    assert len(nodes) == 1
    assert nodes[0].type == "file"
