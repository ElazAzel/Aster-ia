from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from asterion_api.harness import BaseHarness
from asterion_api.schemas import AgentPermissions, AgentPlan

# Windows Job Objects definitions using ctypes
if os.name == "nt":
    import ctypes

    # Constants
    JobObjectExtendedLimitInformationType = 9
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    def _apply_windows_job_limits(pid: int, memory_limit_bytes: int = 512 * 1024 * 1024) -> Any:
        kernel32 = ctypes.windll.kernel32
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_PROCESS_MEMORY |
            JOB_OBJECT_LIMIT_JOB_MEMORY |
            JOB_OBJECT_LIMIT_ACTIVE_PROCESS |
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        info.ProcessMemoryLimit = memory_limit_bytes
        info.JobMemoryLimit = memory_limit_bytes
        info.BasicLimitInformation.ActiveProcessLimit = 2  # main python process + 1 subprocess max

        res = kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformationType,
            ctypes.byref(info),
            ctypes.sizeof(info)
        )
        if not res:
            kernel32.CloseHandle(job)
            return None

        # PROCESS_SET_QUOTA (0x0100) | PROCESS_TERMINATE (0x0001)
        process_handle = kernel32.OpenProcess(0x0100 | 0x0001, False, pid)
        if not process_handle:
            kernel32.CloseHandle(job)
            return None

        success = kernel32.AssignProcessToJobObject(job, process_handle)
        kernel32.CloseHandle(process_handle)
        if not success:
            kernel32.CloseHandle(job)
            return None

        return job


def _set_linux_limits() -> None:
    import resource
    # 512 MB memory limit
    mem_limit = 512 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    # 30 seconds CPU time limit
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    # 10 processes limit
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))


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

    @staticmethod
    def _os_sandbox_kwargs() -> dict[str, Any]:
        import platform
        system = platform.system()
        if system == "Windows":
            return {}
        elif system == "Linux":
            def _preexec():
                import resource
                mem_limit = 512 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
                resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            return {"preexec_fn": _preexec}
        elif system == "Darwin":
            def _preexec_macos():
                import resource
                mem_limit = 512 * 1024 * 1024
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                except (ValueError, resource.error):
                    pass
                try:
                    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
                except (ValueError, resource.error):
                    pass
                try:
                    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
                except (ValueError, resource.error):
                    pass
            return {"preexec_fn": _preexec_macos}
        return {}

    async def run_code(self, *, code: str, permissions: AgentPermissions) -> dict[str, Any]:
        self._validate_code(code, permissions)
        allowed_root = self._allowed_root(permissions)
        script_path = allowed_root / f"agent_{uuid4().hex}.py"
        script_path.write_text(code, encoding="utf-8")
        env = dict(os.environ)
        if not permissions.network:
            env["NO_PROXY"] = "*"
            env["ASTERION_NETWORK_DISABLED"] = "1"
        kwargs = self._os_sandbox_kwargs()

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            cwd=str(allowed_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            **kwargs
        )
        
        job_handle = None
        if os.name == "nt":
            job_handle = _apply_windows_job_limits(proc.pid, 512 * 1024 * 1024)

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        finally:
            if job_handle and os.name == "nt":
                import ctypes
                ctypes.windll.kernel32.CloseHandle(job_handle)

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
        lowered = code.lower()
        if not permissions.shell and any(token in lowered for token in ["subprocess", "os.system"]):
            raise PermissionError("shell permission is disabled")
        if not permissions.network and any(
            token in lowered for token in ["socket", "httpx", "requests", "urllib"]
        ):
            raise PermissionError("network permission is disabled")

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
