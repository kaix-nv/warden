from pathlib import Path
from warden.agents.context import load_understanding, load_relevant_understanding

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


def test_load_relevant_filters_by_keyword(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "design-decisions.md").write_text(
        "# Design Decisions\n\n"
        "## Use SQLite for sessions\n"
        "Chose SQLite over Redis for simplicity.\n\n"
        "## Use async for all I/O\n"
        "Performance requirement for API handlers.\n\n"
        "## Quantization Config Redesign\n"
        "Replaced dict format with ordered list of QuantizerCfgEntry.\n"
    )
    result = load_relevant_understanding(understanding_dir, ["quantization", "QuantizerCfgEntry"])
    assert "Quantization Config" in result
    assert "SQLite" not in result
    assert "async" not in result


def test_load_relevant_returns_all_when_no_keywords(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "design-decisions.md").write_text(
        "# Design Decisions\n\n## Decision A\nContent A.\n\n## Decision B\nContent B.\n"
    )
    result = load_relevant_understanding(understanding_dir, [])
    assert "Content A" in result
    assert "Content B" in result


def test_load_relevant_case_insensitive(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "patterns.md").write_text(
        "# Patterns\n\n## ModeDescriptor pattern\nAll modes use ModeDescriptor.\n"
    )
    result = load_relevant_understanding(understanding_dir, ["modedescriptor"])
    assert "ModeDescriptor" in result
