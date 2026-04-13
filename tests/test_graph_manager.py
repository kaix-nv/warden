from pathlib import Path
from textwrap import dedent
import pytest
from warden.graph.manager import GraphManager

@pytest.fixture
def project(tmp_path):
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

def test_get_dependents(graph):
    deps = graph.get_dependents("myapp/models.py")
    dep_paths = {d["file_path"] for d in deps if d.get("file_path")}
    assert "myapp/service.py" in dep_paths

def test_get_dependencies(graph):
    deps = graph.get_dependencies("myapp/service.py")
    dep_names = {d["qualified_name"] for d in deps}
    assert "myapp.models" in dep_names

def test_get_descendants(graph):
    desc = graph.get_descendants("myapp.models.BaseModel")
    desc_names = {d["qualified_name"] for d in desc}
    assert "myapp.models.User" in desc_names

def test_update_files_incremental(project, graph):
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
    assert "myapp.models.User" in names

def test_update_files_deleted(project, graph):
    (project / "myapp" / "api.py").unlink()
    graph.update_files(changed_files=[], deleted_files=["myapp/api.py"])
    nodes = graph.get_all_nodes()
    names = {n["qualified_name"] for n in nodes}
    assert "myapp.api" not in names
    assert "myapp.models" in names

def test_get_impact_summary(graph):
    summary = graph.get_impact_summary(["myapp/models.py"])
    assert "models.py" in summary
    assert "service.py" in summary or "dependents" in summary.lower()
