import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.graph.client import GraphError, GraphTimeout, QueryNotAllowed

logger = logging.getLogger("app.errors")


class ErrorBody(BaseModel):
    error: str
    message: str
    request_id: str | None = None


class ApiError(Exception):
    """An expected error with a stable code, for example an idempotency conflict."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _json(status: int, code: str, message: str, request_id: str | None = None) -> JSONResponse:
    body = ErrorBody(error=code, message=message, request_id=request_id)
    return JSONResponse(status_code=status, content=body.model_dump(exclude_none=True))


async def _api_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return _json(exc.status_code, exc.code, exc.message)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found"}.get(
        exc.status_code, "http_error"
    )
    return _json(exc.status_code, code, str(exc.detail))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only field locations and short messages, never the submitted values.
    fields = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()
    )
    return _json(422, "validation_error", fields or "Request validation failed.")


async def _graph_timeout(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, GraphTimeout)
    return _json(504, "graph_timeout", "The graph took too long to answer.")


async def _graph_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, GraphError | QueryNotAllowed)
    request_id = uuid.uuid4().hex[:12]
    logger.error("graph error [%s]: %s", request_id, type(exc).__name__)
    return _json(500, "graph_error", "The graph could not complete the request.", request_id)


async def _unknown_error(_: Request, exc: Exception) -> JSONResponse:
    request_id = uuid.uuid4().hex[:12]
    logger.error("unhandled error [%s]", request_id, exc_info=exc)  # stack goes to the log only
    return _json(500, "internal_error", "Something went wrong.", request_id)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(GraphTimeout, _graph_timeout)
    app.add_exception_handler(GraphError, _graph_error)
    app.add_exception_handler(Exception, _unknown_error)