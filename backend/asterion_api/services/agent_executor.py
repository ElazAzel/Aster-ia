from __future__ import annotations

import asyncio


from asterion_api.services.agent_registry import AgentRegistry
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore


class AgentExecutor:
    def __init__(self, store: EncryptedSQLiteStore, registry: AgentRegistry) -> None:
        self.store = store
        self.registry = registry

    async def execute_run(self, run_id: str) -> None:
        run = await self.store.get_agent_run(run_id)
        if not run or run["status"] != "planned":
            return

        # Mark as running
        await self.store.update_agent_run(run_id, status="running")
        await self._log(run_id, "run.started", "AgentExecutor", f"Starting execution of run {run_id}")

        try:
            plan = run["plan"]
            steps = plan.get("steps", [])
            for i, step in enumerate(steps):
                # Check status before each step to handle pause/cancel
                current = await self.store.get_agent_run(run_id)
                if current and current["status"] != "running":
                    await self._log(run_id, "run.halted", "AgentExecutor", f"Run halted with status {current['status']}")
                    return

                await self._log(run_id, "step.executing", "AgentExecutor", f"Executing step {i+1}: {step}")
                
                # Skill bindings
                if "rag-indexing" in step.lower():
                    from asterion_api.dependencies import get_document_indexer
                    get_document_indexer()
                    await self._log(run_id, "skill.rag_indexing", "AgentExecutor", "Calling DocumentIndexer (mock invocation)")
                elif "privacy-radar" in step.lower():
                    from asterion_api.dependencies import get_privacy_analyzer
                    get_privacy_analyzer()
                    await self._log(run_id, "skill.privacy_radar", "AgentExecutor", "Calling PrivacyAnalyzer (mock invocation)")
                
                await asyncio.sleep(0.5)
                await self._log(run_id, "step.completed", "AgentExecutor", f"Completed step {i+1}")

            # Agent handoff logic
            agent_manifest = self.registry.get_agent(run.get("agent_id", ""))
            if agent_manifest and agent_manifest.handoff_targets:
                target = agent_manifest.handoff_targets[0]
                await self.store.update_agent_run(run_id, agent_id=target)
                await self._log(run_id, "run.handoff", "AgentExecutor", f"Handed off task to {target}")

            # Acceptance checks (mocked)
            await self._log(run_id, "run.acceptance_checks", "AgentExecutor", "Running acceptance checks...")
            await asyncio.sleep(0.5)

            await self.store.update_agent_run(run_id, status="completed")
            await self._log(run_id, "run.completed", "AgentExecutor", "Run completed successfully")

        except Exception as e:
            await self.store.update_agent_run(run_id, status="failed")
            await self._log(run_id, "run.failed", "AgentExecutor", f"Run failed: {e}", error=str(e))

    async def _log(
        self, run_id: str, action: str, tool: str, output: str, error: str | None = None
    ) -> None:
        await self.store.append_agent_log(
            run_id=run_id,
            action=action,
            tool=tool,
            privacy_level="local",
            input_text=None,
            output_text=output,
            model=None,
            error=error,
        )
