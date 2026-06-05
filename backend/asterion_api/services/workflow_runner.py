from __future__ import annotations

import asyncio
from typing import Any, Mapping
from uuid import uuid4

from asterion_api.harness import BaseHarness


class WorkflowRunner(BaseHarness):
    privacy_level = "local"

    def __init__(self) -> None:
        self.paused: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return await self.run(dict(payload.get("workflow", {})))

    def get_state(self) -> dict[str, Any]:
        return {"paused_runs": list(self.paused.keys())}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    async def run(self, workflow: dict[str, Any]) -> dict[str, Any]:
        run_id = str(uuid4())
        results = []
        for step in workflow.get("steps", []):
            if step.get("type") == "human_approval":
                future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
                self.paused[run_id] = future
                await self.events.put({"type": "approval_required", "run_id": run_id, "step": step})
                approval = await future
                if not approval.get("approved", False):
                    return {"run_id": run_id, "status": "rejected", "results": results}
            else:
                results.append({"step": step.get("name", "step"), "status": "completed"})
        return {"run_id": run_id, "status": "completed", "results": results}

    def confirm(self, run_id: str, approved: bool, payload: dict[str, Any]) -> bool:
        future = self.paused.pop(run_id, None)
        if future is None or future.done():
            return False
        future.set_result({"approved": approved, "payload": payload})
        return True
