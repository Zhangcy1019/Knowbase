"""UI hosting helpers for the integrated web application."""

from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from internal.utils.config import RuntimeConfig

_UI_DEV_SERVER_PROCESS: subprocess.Popen[str] | None = None


def register_ui_routes(app: FastAPI, *, runtime_cfg: RuntimeConfig, project_root: Path) -> None:
    if runtime_cfg.web.ui.mode == "dev":
        ensure_ui_dev_server(runtime_cfg=runtime_cfg, project_root=project_root)
        register_ui_dev_redirects(app, runtime_cfg=runtime_cfg)
        return

    ui_root = project_root / "ui"
    dist_dir = resolve_ui_dist_dir(runtime_cfg=runtime_cfg, ui_root=ui_root)
    if runtime_cfg.web.ui.enabled is False:
        return

    build_ui_if_needed(runtime_cfg=runtime_cfg, ui_root=ui_root, dist_dir=dist_dir)
    index_file = dist_dir / "index.html"
    if not index_file.exists():
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="knowbase-ui-assets")

    @app.get("/config.json", include_in_schema=False)
    async def get_ui_config() -> JSONResponse:
        return JSONResponse(
            {
                "defaultEnvironment": "preview",
                "environments": [
                    {"id": "preview", "label": "Preview", "websocketUrl": "/ws/chat"},
                    {"id": "release", "label": "Release", "websocketUrl": "/ws/chat"},
                ],
            }
        )

    @app.get("/", include_in_schema=False)
    @app.get("/knowbase", include_in_schema=False)
    async def serve_ui_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_ui_routes(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")
        target = dist_dir / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(index_file)


def resolve_ui_dist_dir(*, runtime_cfg: RuntimeConfig, ui_root: Path) -> Path:
    configured = runtime_cfg.web.ui.dist_dir.strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return ui_root / "dist"


def build_ui_if_needed(*, runtime_cfg: RuntimeConfig, ui_root: Path, dist_dir: Path) -> None:
    if dist_dir.joinpath("index.html").exists():
        return
    if runtime_cfg.web.ui.auto_build is False:
        return
    if not ui_root.joinpath("package.json").exists():
        return
    try:
        subprocess.run(["npm", "run", "build"], cwd=ui_root, check=True)
    except Exception:
        return


def ensure_ui_dev_server(*, runtime_cfg: RuntimeConfig, project_root: Path) -> None:
    global _UI_DEV_SERVER_PROCESS
    if is_port_open(runtime_cfg.web.ui.dev_host, runtime_cfg.web.ui.dev_port):
        return
    if _UI_DEV_SERVER_PROCESS is not None and _UI_DEV_SERVER_PROCESS.poll() is None:
        return

    ui_root = project_root / "ui"
    if not ui_root.joinpath("package.json").exists():
        return

    env = os.environ.copy()
    env["KNOWBASE_UI_DEV_HOST"] = runtime_cfg.web.ui.dev_host
    env["KNOWBASE_UI_DEV_PORT"] = str(runtime_cfg.web.ui.dev_port)
    proxy_host = runtime_cfg.startup.api_server.host
    if proxy_host in {"0.0.0.0", "::"}:
        proxy_host = "127.0.0.1"
    env["KNOWBASE_API_PROXY_TARGET"] = f"http://{proxy_host}:{runtime_cfg.startup.api_server.port}"
    try:
        _UI_DEV_SERVER_PROCESS = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=ui_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        _UI_DEV_SERVER_PROCESS = None


def register_ui_dev_redirects(app: FastAPI, *, runtime_cfg: RuntimeConfig) -> None:
    target_origin = f"http://{runtime_cfg.web.ui.dev_host}:{runtime_cfg.web.ui.dev_port}"

    @app.get("/", include_in_schema=False)
    @app.get("/knowbase", include_in_schema=False)
    async def redirect_ui_index() -> RedirectResponse:
        return RedirectResponse(url=f"{target_origin}/knowbase", status_code=307)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def redirect_ui_routes(full_path: str) -> RedirectResponse:
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")
        return RedirectResponse(url=f"{target_origin}/{full_path}", status_code=307)


def is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False
