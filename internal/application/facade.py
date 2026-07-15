"""Stable facade for top-level application assembly and startup helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from internal.application.container import KnowbaseAppContainer, build_app_container
from internal.application.runtime_env import apply_runtime_config_to_env, load_runtime_config_from_env
from internal.application.ui import register_ui_routes
from internal.utils.config import RuntimeConfig


def build_application_container(*, runtime_cfg: RuntimeConfig) -> KnowbaseAppContainer:
    return build_app_container(runtime_cfg=runtime_cfg)


def configure_runtime_environment(runtime_cfg: RuntimeConfig) -> None:
    apply_runtime_config_to_env(runtime_cfg)


def load_application_runtime_config() -> RuntimeConfig | None:
    return load_runtime_config_from_env()


def attach_ui_routes(app: FastAPI, *, runtime_cfg: RuntimeConfig, project_root: Path) -> None:
    register_ui_routes(app, runtime_cfg=runtime_cfg, project_root=project_root)
