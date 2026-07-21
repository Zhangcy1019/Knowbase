"""Runtime verification components."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "RuntimeAcceptanceVerifier": "internal.runtime.verification.acceptance",
    "RuntimeVerificationProfile": "internal.runtime.verification.profile",
    "RuntimeVerificationContext": "internal.runtime.verification.verifier",
    "RuntimeVerifier": "internal.runtime.verification.verifier",
    "RuntimeVerifierPort": "internal.runtime.verification.verifier",
    "VerificationStopHook": "internal.runtime.verification.stop_hook",
}


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "RuntimeAcceptanceVerifier",
    "RuntimeVerificationProfile",
    "RuntimeVerificationContext",
    "RuntimeVerifier",
    "RuntimeVerifierPort",
    "VerificationStopHook",
]
