from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any

from asterion_api.harness import PrivacyLevel


class StructuredLogger:
    """Small JSON logger with the Asterion privacy fields."""

    def __init__(self, tool: str, privacy_level: PrivacyLevel) -> None:
        self.tool = tool
        self.privacy_level = privacy_level

    def emit(self, action: str, *, error: str | None = None, **fields: Any) -> None:
        event = {
            "ts": datetime.now(UTC).isoformat(),
            "action": action,
            "tool": self.tool,
            "privacy_level": self.privacy_level,
            "error": error,
            **fields,
        }
        print(json.dumps(event, ensure_ascii=True, separators=(",", ":")), file=sys.stdout)
