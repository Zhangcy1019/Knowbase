"""Knowbase API routes."""

from __future__ import annotations

from fastapi import FastAPI

from .deps import KnowbaseRouteDeps
from .routes_core import register_core_routes
from .routes_graph import register_graph_routes
from .routes_resources import register_resource_routes
from .routes_runtime import register_runtime_routes
from .routes_knowledge import register_knowledge_routes


def register_knowbase_routes(app: FastAPI, *, deps: KnowbaseRouteDeps) -> None:
    """Register knowbase routes on the app."""

    register_core_routes(app, deps=deps)
    register_runtime_routes(app, deps=deps)
    register_knowledge_routes(app, deps=deps)
    register_resource_routes(app, deps=deps)
    register_graph_routes(app, deps=deps)


__all__ = ["KnowbaseRouteDeps", "register_knowbase_routes"]
