"""Base subprocess runner with timeout, resource tracking, and WSL support."""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from src.common.types import ExecutionResult, ToolType, StageName
from src.common.exceptions import ToolExecutionError, ToolTimeoutError
from src.common.logger import logger


class ToolRunner:
    """Manages process invocation, stdout/stderr streaming, timeouts, and resource monitoring."""

    def __init__(self, use_wsl: bool = True, wsl_distro: str = "Ubuntu-22.04"):
        self.use_wsl = use_wsl and (sys.platform == "win32")
        self.wsl_distro = wsl_distro

    def _convert_path(self, path: Path | str) -> str:
        """Convert Windows path to WSL path if running via WSL, using space-free symlink if applicable."""
        str_raw = str(path).replace("\\", "/")
        # If already a Linux absolute path (e.g. /opt/..., /usr/..., /mnt/...), preserve it
        if str_raw.startswith(("/", "/opt", "/usr", "/mnt", "/home", "/etc")):
            if not (len(str_raw) > 2 and str_raw[1] == ":"):
                return str_raw

        abs_p = str(Path(path).resolve())
        ws_win = "C:\\Users\\Lenovo\\Desktop\\CAD_AI PROJEC"
        ws_wsl = "/mnt/c/Users/Lenovo/Desktop/CAD_AI PROJEC"

        if abs_p.lower().startswith(ws_win.lower()):
            sub = abs_p[len(ws_win):].replace("\\", "/")
            return f"/opt/cad_ai{sub}"
        elif abs_p.startswith(ws_wsl):
            sub = abs_p[len(ws_wsl):]
            return f"/opt/cad_ai{sub}"

        if not self.use_wsl:
            return abs_p

        drive = abs_p[0].lower()
        rest = abs_p[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"

    def execute(
        self,
        command: List[str],
        workdir: Path,
        stdout_path: Path,
        stderr_path: Path,
        tool: ToolType,
        stage: StageName,
        timeout_s: int = 1800,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute command synchronously with timeout, process cleanup, and stream logging."""
        workdir.mkdir(parents=True, exist_ok=True)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)

        full_cmd = list(command)
        if self.use_wsl:
            # Wrap in WSL invocation
            wsl_workdir = self._convert_path(workdir)
            cmd_str = " ".join(f'"{c}"' if " " in c else c for c in full_cmd)
            full_cmd = ["wsl.exe", "-d", self.wsl_distro, "--", "bash", "-c", f"cd {wsl_workdir} && {cmd_str}"]

        logger.info(f"Executing [{tool.value}] stage [{stage.value}]: {' '.join(command[:4])}...")
        start_time = time.time()

        stdout_file = open(stdout_path, "wb")
        stderr_file = open(stderr_path, "wb")

        proc = None
        try:
            proc = subprocess.Popen(
                full_cmd,
                cwd=str(workdir) if not self.use_wsl else None,
                stdout=stdout_file,
                stderr=stderr_file,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )

            try:
                proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                logger.error(f"Process timed out after {timeout_s}s. Terminating process tree...")
                self._terminate_process(proc)
                stdout_file.close()
                stderr_file.close()
                raise ToolTimeoutError(tool, stage, timeout_s, command)

            runtime_s = round(time.time() - start_time, 3)
            exit_code = proc.returncode

            stdout_file.close()
            stderr_file.close()

            success = (exit_code == 0)

            err_tail = ""
            if stderr_path.exists() and stderr_path.stat().st_size > 0:
                with open(stderr_path, "r", encoding="utf-8", errors="replace") as ef:
                    err_tail = ef.read()[-500:]

            if not success:
                logger.error(f"Execution failed with exit code {exit_code}")
                # Also check stdout if stderr is empty (Yosys prints errors to stdout)
                if not err_tail and stdout_path.exists():
                    with open(stdout_path, "r", encoding="utf-8", errors="replace") as sf:
                        err_tail = sf.read()[-500:]
                raise ToolExecutionError(tool, stage, exit_code, err_tail, command)

            return ExecutionResult(
                tool=tool,
                stage=stage,
                exit_code=exit_code,
                runtime_s=runtime_s,
                peak_memory_mb=0.0,
                stdout_path=str(stdout_path.resolve()),
                stderr_path=str(stderr_path.resolve()),
                success=True
            )

        finally:
            if not stdout_file.closed:
                stdout_file.close()
            if not stderr_file.closed:
                stderr_file.close()

    def _terminate_process(self, proc: subprocess.Popen):
        """Forcefully kill process and all descendants."""
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            logger.warning(f"Failed to kill process {proc.pid}: {e}")
