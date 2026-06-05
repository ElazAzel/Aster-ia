from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Mapping

PrivacyLevel = Literal["local", "hybrid", "external"]


class BaseHarness(ABC):
    """Common optimization interface for Meta-Harness candidate services."""

    privacy_level: PrivacyLevel = "local"

    @abstractmethod
    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        """Run the service's default harness action."""

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return serializable service state for harness inspection."""

    @abstractmethod
    def set_state(self, state: Mapping[str, Any]) -> None:
        """Restore service state from a previous harness candidate."""
