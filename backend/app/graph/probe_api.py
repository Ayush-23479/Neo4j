"""Temporary Task 2 routes, mounted only when DEMO_MODE=probe. Task 5 replaces them.

Relate connections are thread-affine (they must be used on the thread that opened them), so ONE
dedicated worker thread owns the connection and every call is sent to it.
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import relate
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/probe", tags=["probe"])

PATH = os.getenv("PROBE_PATH", "./data/probe.rl")
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="relate")
_conn: relate.Connection | None = None


def _get_conn() -> relate.Connection:  # only ever called on the relate worker thread
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
        _conn = relate.connect(PATH)
    return _conn


def _close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


async def _on_shutdown() -> None:
    await asyncio.get_running_loop().run_in_executor(_executor, _close)


router.add_event_handler("shutdown", _on_shutdown)


class ProbeIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)


def _write(pid: str) -> None:
    _get_conn().execute("MERGE (:Probe {id: $id})", {"id": pid})


def _read() -> list[str]:
    rows = _get_conn().execute("MATCH (n:Probe) RETURN n.id AS id ORDER BY id")
    return [r["id"] for r in rows]


@router.post("/write")
async def write(body: ProbeIn) -> dict[str, str]:
    await asyncio.get_running_loop().run_in_executor(_executor, _write, body.id)
    return {"written": body.id}


@router.get("/read")
async def read() -> dict[str, list[str]]:
    return {"ids": await asyncio.get_running_loop().run_in_executor(_executor, _read)}
