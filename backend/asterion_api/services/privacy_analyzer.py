from __future__ import annotations

from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import PrivacyItem, PrivacyReport


class PrivacyAnalyzer(BaseHarness):
    privacy_level = "local"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> PrivacyReport:
        payload = payload or {}
        return self.analyze(
            model_type=str(payload.get("model_type", "local")),
            files_attached=bool(payload.get("files_attached", False)),
            memory_enabled=bool(payload.get("memory_enabled", False)),
            web_access=bool(payload.get("web_access", False)),
        )

    def get_state(self) -> dict[str, Any]:
        return {"rules": ["model_type", "files_attached", "memory_enabled", "web_access"]}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    def analyze(
        self,
        *,
        model_type: str,
        files_attached: bool,
        memory_enabled: bool,
        web_access: bool,
    ) -> PrivacyReport:
        items: list[PrivacyItem] = []

        if model_type == "api":
            items.append(PrivacyItem(what="model", destination="external_api", risk="red"))
        else:
            items.append(PrivacyItem(what="model", destination="local_ollama", risk="green"))

        if files_attached:
            items.append(
                PrivacyItem(
                    what="files",
                    destination="local_rag" if model_type == "local" else "external_api",
                    risk="yellow" if model_type == "local" else "red",
                )
            )

        if memory_enabled:
            items.append(
                PrivacyItem(
                    what="memory",
                    destination="encrypted_local_sqlcipher",
                    risk="yellow",
                )
            )

        if web_access:
            items.append(
                PrivacyItem(
                    what="web_access",
                    destination="local_searxng_to_public_web",
                    risk="yellow" if model_type == "local" else "red",
                )
            )

        level = "green"
        if any(item.risk == "red" for item in items):
            level = "red"
        elif any(item.risk == "yellow" for item in items):
            level = "yellow"
        return PrivacyReport(level=level, items=items)
