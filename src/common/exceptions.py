"""Strongly-typed exception hierarchy for EDA-Genius."""

from typing import Optional, List
from src.common.types import StageName, ToolType


class EDAGeniusException(Exception):
    """Base class for all EDA-Genius exceptions."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(EDAGeniusException):
    """Raised when configuration, parameters, or file paths are invalid."""
    pass


class RTLValidationError(EDAGeniusException):
    """Raised when RTL syntax or module definition fails validation."""
    pass


class ToolExecutionError(EDAGeniusException):
    """Raised when an external EDA tool process fails."""
    def __init__(
        self,
        tool: ToolType,
        stage: StageName,
        exit_code: int,
        stderr_tail: str,
        command: List[str],
        message: Optional[str] = None
    ):
        msg = message or f"{tool.value} failed at stage {stage.value} with exit code {exit_code}"
        super().__init__(msg, {
            "tool": tool.value,
            "stage": stage.value,
            "exit_code": exit_code,
            "command": " ".join(command),
            "stderr_tail": stderr_tail[-500:] if stderr_tail else ""
        })
        self.tool = tool
        self.stage = stage
        self.exit_code = exit_code
        self.stderr_tail = stderr_tail
        self.command = command


class ToolTimeoutError(ToolExecutionError):
    """Raised when a tool execution exceeds configured walltime."""
    def __init__(self, tool: ToolType, stage: StageName, timeout_s: float, command: List[str]):
        super().__init__(
            tool=tool,
            stage=stage,
            exit_code=-1,
            stderr_tail=f"Execution timed out after {timeout_s} seconds",
            command=command,
            message=f"{tool.value} at stage {stage.value} timed out after {timeout_s}s"
        )
        self.timeout_s = timeout_s


class LogParsingError(EDAGeniusException):
    """Raised when log parser fails to extract required metrics or detects format anomaly."""
    pass


class RecoveryError(EDAGeniusException):
    """Raised when partial run recovery fails."""
    pass
