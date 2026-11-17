"""Transforms ExperimentRecord objects into PostgreSQL-ready entities."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.common.types import ExperimentRecord, ParsedMetric, RunStatus, StageName


class RecordAdapter:
    """Prepares structured experiment outputs for direct PostgreSQL relational ingestion."""

    @staticmethod
    def to_postgres_payload(
        record: ExperimentRecord,
        design_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert an ExperimentRecord to a relational dictionary mapping."""
        resolved_design_id = design_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, record.design_name))

        # Main run record
        run_dict = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, record.run_id)),
            "design_id": resolved_design_id,
            "status": record.status.value,
            "target_pdk": record.target_pdk,
            "clock_period_ns": record.clock_period_ns,
            "tool_versions": record.tool_versions,
            "run_config": {
                "top_module": record.top_module,
                "rtl_hash": record.rtl_hash,
                "config_hash": record.config_hash
            },
            "workdir_path": f"./artifacts/runs/{record.run_id}",
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "total_wall_time_s": record.total_runtime_s
        }

        # Stage records
        stages_list = []
        if record.synthesis_runtime_s > 0:
            stages_list.append({
                "id": str(uuid.uuid4()),
                "run_id": run_dict["id"],
                "stage_name": StageName.SYNTHESIS.value,
                "stage_order": 1,
                "tool_name": "yosys",
                "status": RunStatus.COMPLETED.value if record.failure_stage != StageName.SYNTHESIS else RunStatus.FAILED.value,
                "exit_code": 0 if record.failure_stage != StageName.SYNTHESIS else 1,
                "raw_log_path": record.raw_reports.get("yosys_log"),
                "output_artifact_path": record.artifacts.get("netlist_v"),
                "runtime_s": record.synthesis_runtime_s
            })

        if record.physical_design_runtime_s > 0:
            stages_list.append({
                "id": str(uuid.uuid4()),
                "run_id": run_dict["id"],
                "stage_name": StageName.ROUTING.value,
                "stage_order": 2,
                "tool_name": "openroad",
                "status": RunStatus.COMPLETED.value if record.failure_stage != StageName.ROUTING else RunStatus.FAILED.value,
                "exit_code": 0 if record.failure_stage != StageName.ROUTING else 1,
                "raw_log_path": record.raw_reports.get("openroad_log"),
                "output_artifact_path": record.artifacts.get("def") or record.artifacts.get("odb"),
                "runtime_s": record.physical_design_runtime_s
            })

        # Atomic Stage Metrics
        metrics_list = []
        for metric_name, val in record.metrics.items():
            category = "GENERAL"
            if "cell" in metric_name:
                category = "CELL_COUNT"
            elif "area" in metric_name:
                category = "AREA"
            elif metric_name in ["wns", "tns", "worst_slack"]:
                category = "TIMING"
            elif "power" in metric_name:
                category = "POWER"
            elif "wire" in metric_name or "drc" in metric_name:
                category = "ROUTING"

            metrics_list.append({
                "id": str(uuid.uuid4()),
                "run_id": run_dict["id"],
                "metric_category": category,
                "metric_name": metric_name,
                "float_value": float(val) if isinstance(val, (int, float)) else None,
                "string_value": str(val) if not isinstance(val, (int, float)) else None,
                "recorded_at": datetime.now(timezone.utc).isoformat()
            })

        return {
            "design": {
                "id": resolved_design_id,
                "name": record.design_name,
                "rtl_top_module": record.top_module
            },
            "run": run_dict,
            "stages": stages_list,
            "metrics": metrics_list
        }
