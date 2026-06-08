from __future__ import annotations

import ast
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from asterion_api.harness import BaseHarness
from asterion_api.schemas import AgentPermissions, AgentPlan


class TaskSimulator(BaseHarness):
    privacy_level = "local"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> AgentPlan:
        payload = payload or {}
        return self.plan(str(payload.get("task", "")))

    def get_state(self) -> dict[str, Any]:
        return {"planner": "heuristic"}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    def plan(self, task: str) -> AgentPlan:
        lowered = task.lower()
        permissions = ["file_read"]
        if "write" in lowered or "создай" in lowered or "измен" in lowered:
            permissions.append("file_write")
        if "web" in lowered or "search" in lowered or "поиск" in lowered:
            permissions.append("web_search")
        if "code" in lowered or "python" in lowered:
            permissions.append("run_code")
        return AgentPlan(
            steps=[
                "Clarify local context and inputs",
                "Collect required files or search results",
                "Execute the minimal allowed action",
                "Validate output and summarize changes",
            ],
            required_permissions=permissions,
            estimated_tokens=max(800, min(8000, len(task.split()) * 120)),
        )


SHELL_MODULES = frozenset({"subprocess", "os", "ctypes"})
NETWORK_MODULES = frozenset({"socket", "httpx", "requests", "urllib", "aiohttp", "http.client"})
DANGEROUS_BUILTINS = frozenset({"exec", "eval", "compile", "__import__", "globals", "locals"})


class AgentSandbox(BaseHarness):
    privacy_level = "local"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return await self.run_code(
            code=str(payload.get("code", "")),
            permissions=AgentPermissions(**payload.get("permissions", {})),
        )

    def get_state(self) -> dict[str, Any]:
        return {"subprocess": "python", "network_default": False, "shell_default": False}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    async def run_code(self, *, code: str, permissions: AgentPermissions) -> dict[str, Any]:
        self._validate_code(code, permissions)
        allowed_root = self._allowed_root(permissions)
        script_path = allowed_root / f"agent_{uuid4().hex}.py"
        script_path.write_text(code, encoding="utf-8")
        env = dict(os.environ)
        env.pop("ASTERION_NETWORK_DISABLED", None)
        env.pop("NO_PROXY", None)
        if not permissions.network:
            env["NO_PROXY"] = "*"
            env["ASTERION_NETWORK_DISABLED"] = "1"
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            cwd=str(allowed_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        try:
            script_path.unlink(missing_ok=True)
        except OSError:
            pass
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }

    def file_read(self, path: str, permissions: AgentPermissions) -> str:
        resolved = self._resolve_allowed(path, permissions)
        return resolved.read_text(encoding="utf-8", errors="ignore")

    def file_write(self, path: str, content: str, permissions: AgentPermissions) -> None:
        resolved = self._resolve_allowed(path, permissions)
        resolved.write_text(content, encoding="utf-8")

    def _validate_code(self, code: str, permissions: AgentPermissions) -> None:
        violations: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise PermissionError(f"Syntax error in code: {exc}") from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[0]
                    if not permissions.shell and mod in SHELL_MODULES:
                        violations.append(f"import {alias.name} (shell blocked)")
                    if not permissions.network and mod in NETWORK_MODULES:
                        violations.append(f"import {alias.name} (network blocked)")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split(".")[0]
                    if not permissions.shell and mod in SHELL_MODULES:
                        violations.append(f"from {node.module} import ... (shell blocked)")
                    if not permissions.network and mod in NETWORK_MODULES:
                        violations.append(f"from {node.module} import ... (network blocked)")

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_BUILTINS:
                    if not permissions.shell:
                        violations.append(f"{node.func.id}() call (shell blocked)")

        if violations:
            raise PermissionError("Blocked: " + "; ".join(violations))

    def _allowed_root(self, permissions: AgentPermissions) -> Path:
        if permissions.allowed_folders:
            return Path(permissions.allowed_folders[0]).resolve()
        return Path(tempfile.gettempdir()).resolve()

    def _resolve_allowed(self, path: str, permissions: AgentPermissions) -> Path:
        resolved = Path(path).resolve()
        roots = [Path(folder).resolve() for folder in permissions.allowed_folders]
        if not any(resolved == root or root in resolved.parents for root in roots):
            raise PermissionError("path is outside allowed folders")
        return resolved
