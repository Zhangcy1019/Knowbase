"""Answer synthesis agent skeleton."""

from __future__ import annotations

from internal.models import QueryAnswer
from internal.models.case import KnowbaseCaseSearchHit


class AnswerSynthesisAgent:
    """Generate the final answer from retrieved knowbase artifacts."""

    async def answer(
        self,
        *,
        query: str,
        cases: list[KnowbaseCaseSearchHit],
    ) -> QueryAnswer:
        _ = query
        _ = cases
        return QueryAnswer()
