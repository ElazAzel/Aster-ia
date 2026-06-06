from __future__ import annotations

import re
from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import PrivacyItem, PrivacyReport

# PII Scanners
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s\-.])?\(?\d{3}\)?[\s\-.‌​]?\d{3}[\s\-.‌​]?\d{4}")
RU_PHONE_REGEX = re.compile(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")

ADDRESS_KEYWORDS = [
    r"\bул\.\s+\w+",
    r"\bулица\s+\w+",
    r"\bпр\-кт\s+\w+",
    r"\bпроспект\s+\w+",
    r"\bпер\.\s+\w+",
    r"\bпереулок\s+\w+",
    r"\bг\.\s+\w+",
    r"\bгород\s+\w+",
    r"\bобл\.\s+\w+",
    r"\bобласть\s+\w+",
    r"\bhouse\b",
    r"\bapartment\b",
    r"\bstr\.\s+\w+",
    r"\bstreet\b",
    r"\bavenue\b",
]
ADDRESS_REGEX = re.compile("|".join(ADDRESS_KEYWORDS), re.IGNORECASE)


class PrivacyAnalyzer(BaseHarness):
    privacy_level = "local"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> PrivacyReport:
        payload = payload or {}
        return self.analyze(
            model_type=str(payload.get("model_type", "local")),
            files_attached=bool(payload.get("files_attached", False)),
            memory_enabled=bool(payload.get("memory_enabled", False)),
            web_access=bool(payload.get("web_access", False)),
            prompt=payload.get("prompt") if payload.get("prompt") is not None else None,
        )

    def get_state(self) -> dict[str, Any]:
        return {"rules": ["model_type", "files_attached", "memory_enabled", "web_access", "prompt"]}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    def analyze(
        self,
        *,
        model_type: str,
        files_attached: bool,
        memory_enabled: bool,
        web_access: bool,
        prompt: str | None = None,
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

        # Scan for PII in the prompt text
        if prompt:
            if EMAIL_REGEX.search(prompt):
                items.append(
                    PrivacyItem(
                        what="pii_email",
                        destination="prompt_data",
                        risk="red" if model_type == "api" else "yellow",
                    )
                )
            if PHONE_REGEX.search(prompt) or RU_PHONE_REGEX.search(prompt):
                items.append(
                    PrivacyItem(
                        what="pii_phone",
                        destination="prompt_data",
                        risk="red" if model_type == "api" else "yellow",
                    )
                )
            if ADDRESS_REGEX.search(prompt):
                items.append(
                    PrivacyItem(
                        what="pii_address",
                        destination="prompt_data",
                        risk="red" if model_type == "api" else "yellow",
                    )
                )

        level = "green"
        if any(item.risk == "red" for item in items):
            level = "red"
        elif any(item.risk == "yellow" for item in items):
            level = "yellow"
        return PrivacyReport(level=level, items=items)
