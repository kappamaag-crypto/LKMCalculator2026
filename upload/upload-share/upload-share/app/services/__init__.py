"""Application services."""

from .calculation_service import CalculationService
from .recommendation_service import RecommendationService

__all__ = ["CalculationService", "RecommendationService", "HistoryService"]


def __getattr__(name: str):
    if name == "HistoryService":
        from .history_service import HistoryService
        return HistoryService
    raise AttributeError(name)
