"""Helpers for projecting verification outcomes back into runtime observations."""

from __future__ import annotations


def build_verification_feedback_payload(*, summary: str, repair_prompt: str, issues: list[str]) -> dict[str, object]:
    """Build a compact payload that the main loop can consume on retry."""

    return {
        "summary": summary,
        "repair_prompt": repair_prompt,
        "issues": list(issues),
    }
