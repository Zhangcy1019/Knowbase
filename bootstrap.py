"""Application bootstrap for the integrated Knowbase web app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

PROJECT_ROOT = Path(__file__).resolve().parent

from internal.application import (
    attach_ui_routes,
    build_application_container,
    load_application_runtime_config,
)
from internal.api import register_knowbase_routes
from internal.utils.config import RuntimeConfig

_RUNTIME_CFG: RuntimeConfig | None = None


def create_app(*, runtime_cfg: RuntimeConfig | None = None) -> FastAPI:
    resolved_runtime_cfg = runtime_cfg or _RUNTIME_CFG or load_application_runtime_config()
    if resolved_runtime_cfg is None:
        raise RuntimeError("runtime config could not be loaded")
    app = FastAPI(title="Knowbase API", version="0.1.0")
    container = build_application_container(runtime_cfg=resolved_runtime_cfg)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    register_knowbase_routes(
        app,
        deps=container.route_deps,
    )
    attach_ui_routes(app, runtime_cfg=resolved_runtime_cfg, project_root=PROJECT_ROOT)
    return app
