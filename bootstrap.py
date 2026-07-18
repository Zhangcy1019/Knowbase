"""Application bootstrap for the integrated Knowbase web app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parent

from internal.application import (
    attach_ui_routes,
    build_application_container,
)
from internal.api import register_knowbase_routes
from internal.utils.logger import get_logger
from internal.utils.config import RuntimeConfig

_RUNTIME_CFG: RuntimeConfig | None = None
logger = get_logger("knowbase.bootstrap")


def set_runtime_config(runtime_cfg: RuntimeConfig) -> None:
    global _RUNTIME_CFG
    _RUNTIME_CFG = runtime_cfg


def create_app(*, runtime_cfg: RuntimeConfig | None = None) -> FastAPI:
    resolved_runtime_cfg = runtime_cfg or _RUNTIME_CFG
    if resolved_runtime_cfg is None:
        raise RuntimeError("runtime config is not set")
    app = FastAPI(title="Knowbase API", version="0.1.0")
    container = build_application_container(runtime_cfg=resolved_runtime_cfg)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": message,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled request error",
            extra={
                "context": {
                    "method": request.method,
                    "path": request.url.path,
                }
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc) or "Internal server error",
                "status_code": 500,
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    register_knowbase_routes(
        app,
        deps=container.route_deps,
    )
    attach_ui_routes(app, runtime_cfg=resolved_runtime_cfg, project_root=PROJECT_ROOT)
    return app
