from pathlib import Path
from warden.agents.context import load_understanding

def test_load_understanding_empty_dir(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    result = load_understanding(understanding_dir)
    assert result == ""

def test_load_understanding_with_docs(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "architecture.md").write_text("# Architecture\nMicroservices.\n")
    (understanding_dir / "design-decisions.md").write_text("# Decisions\nUse SQLite.\n")
    result = load_understanding(understanding_dir)
    assert "Microservices" in result
    assert "Use SQLite" in result

def test_load_understanding_skips_empty_files(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "architecture.md").write_text("")
    (understanding_dir / "patterns.md").write_text("# Patterns\nSome pattern.\n")
    result = load_understanding(understanding_dir)
    assert "architecture" not in result.lower()
    assert "Some pattern" in result
