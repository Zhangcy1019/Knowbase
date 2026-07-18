"""Stable facade for top-level application assembly and startup helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from internal.application.container import KnowbaseAppContainer, build_app_container
from internal.application.ui import register_ui_routes
from internal.utils.config import RuntimeConfig, load_runtime_config


def build_application_container(*, runtime_cfg: RuntimeConfig) -> KnowbaseAppContainer:
    return build_app_container(runtime_cfg=runtime_cfg)


def load_application_runtime_config(config_path: str) -> RuntimeConfig:
    return load_runtime_config(config_path)


def attach_ui_routes(app: FastAPI, *, runtime_cfg: RuntimeConfig, project_root: Path) -> None:
    register_ui_routes(app, runtime_cfg=runtime_cfg, project_root=project_root)
