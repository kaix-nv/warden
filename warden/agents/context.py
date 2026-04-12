from pathlib import Path

UNDERSTANDING_DOCS = ["architecture.md", "design-decisions.md", "patterns.md"]

def load_understanding(understanding_dir: Path) -> str:
    """Load all understanding docs as a single string for prompt context."""
    parts = []
    for doc_name in UNDERSTANDING_DOCS:
        doc_path = understanding_dir / doc_name
        if doc_path.exists():
            content = doc_path.read_text().strip()
            if content:
                parts.append(f"### {doc_name}\n\n{content}")
    return "\n\n---\n\n".join(parts)
