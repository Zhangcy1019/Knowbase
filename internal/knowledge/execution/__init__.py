"""Execution of validated Knowledge mutations."""

from internal.knowledge.execution.mutation_executor import KnowledgeMutationExecutor, MutationApplyResult
from internal.knowledge.model.mutation_plan import KnowledgeMutationPlan

__all__ = ["KnowledgeMutationExecutor", "KnowledgeMutationPlan", "MutationApplyResult"]
