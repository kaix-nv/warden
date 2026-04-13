import re
from pathlib import Path

UNDERSTANDING_DOCS = ["architecture.md", "relationships.md", "design-decisions.md", "patterns.md"]


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


def load_relevant_understanding(understanding_dir: Path, keywords: list[str]) -> str:
    """Load only sections from understanding docs that mention any keyword."""
    if not keywords:
        return load_understanding(understanding_dir)

    # Normalize keywords for case-insensitive matching
    lower_keywords = [k.lower() for k in keywords]

    parts = []
    for doc_name in UNDERSTANDING_DOCS:
        doc_path = understanding_dir / doc_name
        if not doc_path.exists():
            continue
        content = doc_path.read_text().strip()
        if not content:
            continue

        # Split into sections on ## headings
        sections = re.split(r'\n(?=## )', content)
        matching = []
        for section in sections:
            section_lower = section.lower()
            if any(kw in section_lower for kw in lower_keywords):
                matching.append(section.strip())

        if matching:
            parts.append(f"### {doc_name} (relevant sections)\n\n" + "\n\n".join(matching))

    return "\n\n---\n\n".join(parts)
