"""Normalization of case and query semantic observations."""

from __future__ import annotations

from internal.knowledge.statistics.models import CaseObservation, QueryObservation, SemanticObservation


class StatisticsObservationNormalizer:
    """Apply lightweight structural normalization before aggregation."""

    def normalize(self, observation: SemanticObservation) -> SemanticObservation:
        data = observation.model_dump()
        for field in ("facets", "semantic_profile", "facts"):
            data[field] = self._normalize_mapping(data[field])
        return type(observation).model_validate(data)

    def normalize_case(self, observation: CaseObservation) -> CaseObservation:
        return self.normalize(observation)  # type: ignore[return-value]

    def normalize_query(self, observation: QueryObservation) -> QueryObservation:
        return self.normalize(observation)  # type: ignore[return-value]

    @staticmethod
    def _normalize_mapping(values: dict[str, list[str]]) -> dict[str, list[str]]:
        normalized: dict[str, list[str]] = {}
        for raw_key, raw_values in values.items():
            key = str(raw_key).strip().casefold()
            if not key:
                continue
            unique_values = sorted({str(value).strip() for value in raw_values if str(value).strip()})
            if unique_values:
                normalized[key] = unique_values
        return normalized


__all__ = ["StatisticsObservationNormalizer"]
