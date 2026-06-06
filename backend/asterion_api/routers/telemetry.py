from __future__ import annotations

import logging
from typing import Any
import httpx
from fastapi import APIRouter

from asterion_api.schemas import TelemetryReportRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.post("/report")
async def report_telemetry(payload: TelemetryReportRequest) -> dict[str, Any]:
    if not payload.opt_in:
        return {"status": "skipped", "reason": "opt_out"}

    # Strictly hybrid/external operations - post to external URL
    telemetry_url = "https://telemetry.asterion.ai/api/report"

    anonymized_data = {
        "event_type": payload.event_type,
        "details": payload.details,
        "vram_gb": payload.vram_gb,
        "ram_gb": payload.ram_gb,
        "os_platform": payload.os_platform
    }

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(telemetry_url, json=anonymized_data)
            if response.status_code == 200:
                return {"status": "success"}
            else:
                return {"status": "failed", "detail": f"HTTP {response.status_code}"}
    except httpx.HTTPError as exc:
        # Gracefully handle connection error since it's an external server
        logger.warning(f"Telemetry server unreachable: {exc}")
        return {"status": "failed", "detail": "connection_error"}
