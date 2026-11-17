"""Configuration loader using YAML and environment variables."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    binary_path: str
    version_command: str = "-V"
    default_timeout_s: int = 1800


class PDKConfig(BaseModel):
    name: str
    tech_lef: Optional[str] = None
    std_cell_lef: Optional[str] = None
    liberty_file: Optional[str] = None
    rcx_rules: Optional[str] = None


class SystemConfig(BaseModel):
    artifacts_root: Path = Path("./artifacts")
    runs_dir: Path = Path("./artifacts/runs")
    reports_dir: Path = Path("./artifacts/reports")
    database_url: str = "postgresql+asyncpg://eda_user:eda_password@localhost:5432/eda_genius"
    wsl_enabled: bool = True
    wsl_distribution: str = "Ubuntu-22.04"
    tools: Dict[str, ToolConfig] = Field(default_factory=dict)
    pdks: Dict[str, PDKConfig] = Field(default_factory=dict)


def load_config(config_dir: Optional[Path] = None) -> SystemConfig:
    """Load configuration from YAML files with defaults."""
    cfg_dir = config_dir or Path("./configs")
    base_file = cfg_dir / "base_config.yaml"
    tool_file = cfg_dir / "eda_toolchains.yaml"

    cfg = SystemConfig()

    if base_file.exists():
        with open(base_file, "r") as f:
            data = yaml.safe_load(f) or {}
            if "paths" in data:
                cfg.artifacts_root = Path(data["paths"].get("artifacts_root", cfg.artifacts_root))
                cfg.runs_dir = Path(data["paths"].get("runs_dir", cfg.runs_dir))
            if "database" in data:
                cfg.database_url = data["database"].get("url", cfg.database_url)

    if tool_file.exists():
        with open(tool_file, "r") as f:
            data = yaml.safe_load(f) or {}
            if "tools" in data:
                for t_name, t_val in data["tools"].items():
                    cfg.tools[t_name] = ToolConfig(**t_val)
            if "pdks" in data:
                for p_name, p_val in data["pdks"].items():
                    cfg.pdks[p_name] = PDKConfig(**p_val)

    # Ensure runtime directories exist
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.reports_dir.mkdir(parents=True, exist_ok=True)

    return cfg
