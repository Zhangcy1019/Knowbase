"""Application facade for knowbase top-level entrypoints."""

from internal.application.container import KnowbaseAppContainer
from internal.application.facade import (
    attach_ui_routes,
    build_application_container,
    load_application_runtime_config,
)

__all__ = [
    "KnowbaseAppContainer",
    "attach_ui_routes",
    "build_application_container",
    "load_application_runtime_config",
]
