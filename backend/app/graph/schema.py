import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.graph.client import GraphClient


def schema_path() -> Path:
    """Find graph/schema.cypher: env override, Docker mount, then the repo checkout."""
    candidates: list[Path] = []
    env = os.getenv("GRAPH_SCHEMA_PATH")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("/app/graph/schema.cypher"))  # mounted by docker-compose
    candidates.append(Path(__file__).resolve().parents[3] / "graph" / "schema.cypher")
    candidates.append(Path.cwd().parent / "graph" / "schema.cypher")  # run from backend/
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(f"graph/schema.cypher not found. Looked in: {searched}")


def read_statements(path: Path | None = None) -> list[str]:
    """Return the statements of the schema file (blank lines and // comments removed)."""
    text = (path or schema_path()).read_text(encoding="utf-8")
    statements: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        statements.append(line)
    return statements


async def apply_schema(client: "GraphClient", path: Path | None = None) -> int:
    """Run every schema statement through the GraphClient. Returns how many ran."""
    statements = read_statements(path)
    await client.run_schema(statements)
    return len(statements)