from __future__ import annotations

import asyncio
import sys
from typing import Any, Mapping
from uuid import uuid4

from asterion_api.harness import BaseHarness
from asterion_api.structured_logging import StructuredLogger
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore


class WorkflowRunner(BaseHarness):
    privacy_level = "local"

    def __init__(self, store: EncryptedSQLiteStore) -> None:
        self.store = store
        self.paused: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.logger = StructuredLogger("workflow", self.privacy_level)

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return await self.run(dict(payload.get("workflow", {})))

    def get_state(self) -> dict[str, Any]:
        return {"paused_runs": list(self.paused.keys())}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    async def run(self, workflow: dict[str, Any]) -> dict[str, Any]:
        run_id = str(uuid4())
        results: list[dict[str, Any]] = []

        await self.store.save_workflow_run(run_id, "running", workflow, results)
        self.logger.emit("workflow.started", run_id=run_id)

        for step in workflow.get("steps", []):
            step_name = step.get("name", "unnamed")
            step_type = step.get("type", "tool_call")

            if step_type == "human_approval":
                future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
                self.paused[run_id] = future
                await self.store.save_workflow_run(run_id, "paused", workflow, results)
                await self.events.put({"type": "approval_required", "run_id": run_id, "step": step})
                self.logger.emit("workflow.paused", run_id=run_id, step=step_name)
                try:
                    approval = await asyncio.wait_for(future, timeout=3600)
                except asyncio.TimeoutError:
                    await self.store.save_workflow_run(run_id, "timeout", workflow, results)
                    return {"run_id": run_id, "status": "timeout", "results": results}
                if not approval.get("approved", False):
                    await self.store.save_workflow_run(run_id, "rejected", workflow, results)
                    self.logger.emit("workflow.rejected", run_id=run_id, step=step_name)
                    return {"run_id": run_id, "status": "rejected", "results": results}
                results.append({"step": step_name, "status": "approved", "payload": approval.get("payload")})
                await self.store.save_workflow_run(run_id, "running", workflow, results)

            elif step_type == "tool_call":
                result = await self._execute_tool_call(step)
                results.append({"step": step_name, "status": "completed", "result": result})
                await self.store.save_workflow_run(run_id, "running", workflow, results)
                self.logger.emit("workflow.step_completed", run_id=run_id, step=step_name)

            elif step_type == "code_exec":
                result = await self._execute_code(step)
                results.append({"step": step_name, "status": "completed", "result": result})
                await self.store.save_workflow_run(run_id, "running", workflow, results)
                self.logger.emit("workflow.step_completed", run_id=run_id, step=step_name)

            elif step_type == "condition":
                passed = self._evaluate_condition(step, results)
                results.append({"step": step_name, "status": "completed", "passed": passed})
                await self.store.save_workflow_run(run_id, "running", workflow, results)
                if not passed and step.get("abort_on_false", False):
                    await self.store.save_workflow_run(run_id, "failed", workflow, results)
                    self.logger.emit("workflow.condition_failed", run_id=run_id, step=step_name)
                    return {"run_id": run_id, "status": "failed", "results": results}

            else:
                results.append({"step": step_name, "status": "skipped", "reason": f"unknown type: {step_type}"})
                await self.store.save_workflow_run(run_id, "running", workflow, results)

        await self.store.save_workflow_run(run_id, "completed", workflow, results)
        self.logger.emit("workflow.completed", run_id=run_id, steps=len(results))
        return {"run_id": run_id, "status": "completed", "results": results}

    async def _execute_tool_call(self, step: dict[str, Any]) -> dict[str, Any]:
        tool = step.get("tool", "")
        args = step.get("args", {})
        self.logger.emit("workflow.tool_call", tool=tool)
        return {"tool": tool, "args": args, "output": f"Tool '{tool}' executed (stub)"}

    async def _execute_code(self, step: dict[str, Any]) -> dict[str, Any]:
        code = step.get("code", "pass")
        timeout = step.get("timeout", 30)
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except asyncio.TimeoutError:
            return {"exit_code": -1, "error": f"code_exec timed out after {timeout}s"}
        except Exception as exc:
            return {"exit_code": -1, "error": str(exc)}

    def _evaluate_condition(self, step: dict[str, Any], results: list[dict[str, Any]]) -> bool:
        condition = step.get("condition", "")
        if not condition:
            return True
        last_result = results[-1] if results else {}
        try:
            eval_env = {"results": results, "last": last_result}
            return bool(eval(condition, {"__builtins__": {}}, eval_env))
        except Exception:
            return False

    def confirm(self, run_id: str, approved: bool, payload: dict[str, Any]) -> bool:
        future = self.paused.pop(run_id, None)
        if future is None or future.done():
            async def update_db_only():
                run = await self.store.get_workflow_run(run_id)
                if run and run["status"] == "paused":
                    status = "completed" if approved else "rejected"
                    await self.store.save_workflow_run(run_id, status, run["workflow"], run["results"])
            asyncio.create_task(update_db_only())
            return future is not None

        future.set_result({"approved": approved, "payload": payload})
        return True
