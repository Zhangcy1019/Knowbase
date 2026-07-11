"""Backward-compatible planner alias for the runtime agent."""

from __future__ import annotations

from internal.runtime.agent import DeterministicRuntimeAgent, RuntimeAgentPort


AgentPlannerPort = RuntimeAgentPort
DeterministicAgentPlanner = DeterministicRuntimeAgent


__all__ = ["AgentPlannerPort", "DeterministicAgentPlanner"]
