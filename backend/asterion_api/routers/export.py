from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from asterion_api.dependencies import get_store
from asterion_api.schemas import ExportFormat, ExportRequest, ExportScope
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("")
async def export_data(
    request: ExportRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> Response:
    data = await _collect_data(scope=request.scope, room_id=request.room_id, store=store)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"asterion_export_{request.scope.value}_{timestamp}"

    if request.format == ExportFormat.JSON:
        content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        return Response(
            content=content.encode("utf-8"),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )
    elif request.format == ExportFormat.MARKDOWN:
        content = _to_markdown(data, scope=request.scope)
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}.md"'},
        )
    else:
        content = _to_csv(data)
        return Response(
            content=content.encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )


async def _collect_data(scope: ExportScope, room_id: str | None,
                         store: EncryptedSQLiteStore) -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = {}

    if scope in (ExportScope.ALL, ExportScope.ARTIFACTS):
        data["artifacts"] = await store.list_artifacts(room_id)

    if scope in (ExportScope.ALL, ExportScope.MEMORIES):
        rid = room_id or "default"
        data["memories"] = await store.list_memories(rid)

    if scope in (ExportScope.ALL, ExportScope.CONVERSATIONS):
        data["conversations"] = await store.list_conversations(room_id=room_id)

    if scope in (ExportScope.ALL, ExportScope.RESEARCH):
        data["research_receipts"] = await store.get_all_research_receipts()

    if scope in (ExportScope.ALL, ExportScope.AUDIT_LOGS):
        data["audit_logs"] = await store.list_audit_logs()

    return data


def _to_markdown(data: dict[str, list[dict]], scope: ExportScope) -> str:
    lines = [f"# Asterion AI Export -- {scope.value}",
             f"Generated: {datetime.now(UTC).isoformat()}", ""]

    for section, records in data.items():
        lines.append(f"## {section.replace('_', ' ').title()} ({len(records)})")
        if not records:
            lines.append("_No records_")
        else:
            headers = list(records[0].keys())
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for rec in records[:100]:
                row = " | ".join(str(rec.get(h, ""))[:80] for h in headers)
                lines.append(f"| {row} |")
        lines.append("")
    return "\n".join(lines)


def _to_csv(data: dict[str, list[dict]]) -> str:
    output = io.StringIO()
    for section, records in data.items():
        if not records:
            continue
        output.write(f"# {section}\n")
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
        writer.writeheader()
        for rec in records:
            writer.writerow({k: str(v)[:500] for k, v in rec.items()})
        output.write("\n")
    return output.getvalue()
