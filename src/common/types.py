"""Core domain types, enums, and data models for EDA-Genius."""

from enum import Enum
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ToolType(str, Enum):
    YOSYS = "yosys"
    OPENROAD = "openroad"


class StageName(str, Enum):
    VALIDATION = "VALIDATION"
    SYNTHESIS = "SYNTHESIS"
    FLOORPLAN = "FLOORPLAN"
    PLACEMENT = "PLACEMENT"
    CTS = "CTS"
    ROUTING = "ROUTING"
    SIGNOFF = "SIGNOFF"


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    RECOVERED = "RECOVERED"


class AnomalySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class ExecutionResult(BaseModel):
    """Result of an individual tool execution or stage."""
    tool: ToolType
    stage: StageName
    exit_code: int
    runtime_s: float
    peak_memory_mb: float = 0.0
    stdout_path: str
    stderr_path: str
    artifact_paths: Dict[str, str] = Field(default_factory=dict)
    success: bool
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParsedMetric(BaseModel):
    """Atomic metric extracted from tool logs or reports with exact provenance."""
    category: str  # 'TIMING', 'AREA', 'POWER', 'CELL_COUNT', 'CONGESTION'
    name: str      # e.g., 'wns', 'tns', 'total_cells', 'die_area_um2'
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    line_number: Optional[int] = None
    byte_offset: Optional[int] = None
    raw_snippet: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DesignInput(BaseModel):
    """RTL design input specification."""
    design_name: str
    top_module: str
    verilog_files: List[Path]
    clock_period_ns: float = 10.0
    clock_port_name: str = "clk"
    reset_port_name: str = "rst_n"
    target_pdk: str = "sky130hd"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    core_utilization: float = 0.50
    aspect_ratio: float = 1.0
    core_space_um: float = 10.0


class ExperimentRecord(BaseModel):
    """Complete structured record of an EDA experiment run."""
    run_id: str
    design_name: str
    top_module: str
    status: RunStatus
    rtl_hash: str
    config_hash: str
    tool_versions: Dict[str, str]
    target_pdk: str
    clock_period_ns: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_runtime_s: float = 0.0
    synthesis_runtime_s: float = 0.0
    physical_design_runtime_s: float = 0.0
    failure_stage: Optional[StageName] = None
    error_summary: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    cell_statistics: Dict[str, int] = Field(default_factory=dict)
    artifacts: Dict[str, str] = Field(default_factory=dict)
    raw_reports: Dict[str, str] = Field(default_factory=dict)
