import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import relate

logger = logging.getLogger("app.graph")

NAME_RE = re.compile(r"^[a-z0-9_]+$")


class GraphError(Exception):
    """Base class for graph access errors."""


class GraphTimeout(GraphError):
    """A query took longer than its time budget."""


class QueryNotAllowed(GraphError):
    """The query name is badly formed or no such named query exists."""


def find_query_dir(configured: str | None = None) -> Path:
    """Locate graph/queries: env/config, Docker mount, then the repo checkout."""
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    env = os.getenv("GRAPH_QUERY_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("/app/graph/queries"))  # mounted by docker-compose
    candidates.append(Path(__file__).resolve().parents[3] / "graph" / "queries")
    candidates.append(Path.cwd().parent / "graph" / "queries")  # run from backend/
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    searched = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(f"graph/queries not found. Looked in: {searched}")


class GraphClient:
    def __init__(
        self,
        path: str,
        query_dir: str | Path | None = None,
        default_limit: int = 100,
        default_timeout_s: float = 5.0,
    ) -> None:
        self._path = path
        self._query_dir = Path(query_dir) if query_dir else find_query_dir()
        self._default_limit = default_limit
        self._default_timeout_s = default_timeout_s
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="relate")
        self._conn: Any = None  # only ever touched on the worker thread
        # Services that need "check then write" take this lock (one API worker only).
        self.write_lock = asyncio.Lock()

    # ---- worker-thread side -------------------------------------------------
    def _get_conn(self) -> Any:
        if self._conn is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = relate.connect(self._path)
        return self._conn

    def _close_conn(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _blocking_run(self, text: str, params: dict[str, Any], limit: int) -> list[dict]:
        cursor = self._get_conn().execute(text, params)
        return [row.data() for row in cursor.fetchmany(limit)]

    def _blocking_schema(self, statements: list[str]) -> None:
        conn = self._get_conn()
        for statement in statements:
            conn.execute(statement)

    # ---- caller side --------------------------------------------------------
    def _load(self, name: str) -> str:
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise QueryNotAllowed("Query names use only a-z, 0-9 and underscore.")
        path = self._query_dir / f"{name}.cypher"
        if not path.is_file():
            raise QueryNotAllowed(f"No named query called {name!r}.")
        return path.read_text(encoding="utf-8")

    async def _run(
        self, name: str, params: dict[str, Any] | None, limit: int | None, timeout_s: float | None
    ) -> list[dict]:
        text = self._load(name)
        max_rows = limit if limit is not None else self._default_limit
        budget = timeout_s if timeout_s is not None else self._default_timeout_s
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(
            self._executor, self._blocking_run, text, dict(params or {}), max_rows
        )
        try:
            return await asyncio.wait_for(future, timeout=budget)
        except TimeoutError as exc:
            # The Relate Python library cannot cancel a running query, so a timeout frees
            # the caller but the query may still finish in the background.
            logger.warning("graph query %s timed out after %.1fs", name, budget)
            raise GraphTimeout(f"Query {name!r} exceeded {budget} seconds.") from exc

    async def run_named(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        limit: int | None = None,
        timeout_s: float | None = None,
    ) -> list[dict]:
        """Run a named read query with parameters. Returns at most `limit` rows."""
        return await self._run(name, params, limit, timeout_s)

    async def run_write(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        limit: int | None = None,
        timeout_s: float | None = None,
    ) -> list[dict]:
        """Run a named write query (MERGE/CREATE/SET) with parameters."""
        return await self._run(name, params, limit, timeout_s)

    async def run_schema(self, statements: list[str]) -> None:
        """Run schema statements. For startup only, never with request data."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._blocking_schema, list(statements))

    async def close(self) -> None:
        """Close the connection on its own thread, then stop the thread."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._close_conn)
        self._executor.shutdown(wait=True)