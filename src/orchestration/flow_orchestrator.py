"""End-to-end reproducible EDA flow orchestrator."""

import os
import sys
import json
import csv
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import uuid


def _now() -> datetime:
    """Return current UTC time as timezone-aware datetime (Python 3.12+ safe)."""
    return datetime.now(timezone.utc)


from src.common.types import (
    DesignInput,
    ExperimentRecord,
    RunStatus,
    StageName,
    ToolType,
    ExecutionResult,
    ParsedMetric
)
from src.common.exceptions import (
    ConfigurationError,
    RTLValidationError,
    ToolExecutionError,
    ToolTimeoutError,
    RecoveryError
)
from src.orchestration.tool_runner import ToolRunner
from src.orchestration.yosys_runner import YosysRunner
from src.orchestration.openroad_runner import OpenROADRunner
from src.common.logger import logger


class FlowOrchestrator:
    """Orchestrates RTL validation -> Yosys synthesis -> OpenROAD physical design -> PPA reports."""

    def __init__(
        self,
        runs_dir: Path = Path("./artifacts/runs"),
        reports_dir: Path = Path("./artifacts/reports"),
        tool_runner: Optional[ToolRunner] = None,
        yosys_binary: str = "yosys",
        openroad_binary: str = "/opt/eda_env/bin/openroad",
        use_wsl: bool = True
    ):
        self.runs_dir = runs_dir
        self.reports_dir = reports_dir
        self.runner = tool_runner or ToolRunner(use_wsl=use_wsl)
        self.yosys_runner = YosysRunner(runner=self.runner, yosys_binary=yosys_binary)
        self.openroad_runner = OpenROADRunner(runner=self.runner, openroad_binary=openroad_binary)

    def compute_rtl_hash(self, verilog_files: List[Path]) -> str:
        """Compute aggregate SHA-256 hash across all input RTL files for lineage tracking."""
        hasher = hashlib.sha256()
        for vf in sorted(verilog_files):
            with open(vf, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        return hasher.hexdigest()

    def compute_config_hash(self, config_dict: Dict[str, Any]) -> str:
        """Compute deterministic SHA-256 hash of design parameters and constraints."""
        serialized = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def validate_rtl_inputs(self, design_input: DesignInput):
        """Validate input files exist and match Verilog/SystemVerilog standards."""
        if not design_input.verilog_files:
            raise ConfigurationError(f"No RTL source files specified for design {design_input.design_name}")

        for vf in design_input.verilog_files:
            if not vf.exists():
                raise RTLValidationError(f"RTL source file not found: {vf}")
            if vf.suffix.lower() not in [".v", ".sv", ".verilog"]:
                raise RTLValidationError(f"Invalid RTL extension '{vf.suffix}' for file: {vf}")

        if not design_input.top_module or not design_input.top_module.isidentifier():
            raise RTLValidationError(f"Invalid top module name identifier: {design_input.top_module}")

    def execute_flow(
        self,
        design_input: DesignInput,
        pdk_config: Optional[Dict[str, Any]] = None,
        run_physical_design: bool = False,
        recover_run_id: Optional[str] = None,
        max_retries: int = 1
    ) -> ExperimentRecord:
        """Execute the end-to-end EDA pipeline with reliability, retry policies, and tracking."""
        start_time = _now()
        run_id = recover_run_id or f"run_{design_input.design_name}_{uuid.uuid4().hex[:8]}"
        workdir = self.runs_dir / run_id
        workdir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting EDA flow for design [{design_input.design_name}] (run_id: {run_id})")

        # 1. RTL Input validation
        self.validate_rtl_inputs(design_input)
        rtl_hash = self.compute_rtl_hash(design_input.verilog_files)
        config_hash = self.compute_config_hash({
            "top_module": design_input.top_module,
            "clock_period_ns": design_input.clock_period_ns,
            "target_pdk": design_input.target_pdk,
            "core_utilization": design_input.core_utilization,
            "aspect_ratio": design_input.aspect_ratio,
            "parameters": design_input.parameters
        })

        record = ExperimentRecord(
            run_id=run_id,
            design_name=design_input.design_name,
            top_module=design_input.top_module,
            status=RunStatus.RUNNING,
            rtl_hash=rtl_hash,
            config_hash=config_hash,
            tool_versions={"yosys": "0.9+", "openroad": "2.0+"},
            target_pdk=design_input.target_pdk,
            clock_period_ns=design_input.clock_period_ns,
            started_at=start_time
        )

        all_metrics: Dict[str, Any] = {}
        failure_stage: Optional[StageName] = None
        error_summary: Optional[str] = None

        synth_result: Optional[ExecutionResult] = None
        synth_metrics: List[ParsedMetric] = []
        netlist_path = workdir / f"{design_input.top_module}_synth.v"

        # 2. Stage: Synthesis (with partial-run recovery)
        if recover_run_id and netlist_path.exists() and netlist_path.stat().st_size > 0:
            logger.info(f"Partial-run recovery: Found existing synthesized netlist at {netlist_path}. Skipping synthesis.")
            record.status = RunStatus.RECOVERED
        else:
            attempt = 0
            while attempt <= max_retries:
                try:
                    liberty_path = pdk_config.get("liberty_file") if pdk_config else None
                    synth_result, synth_metrics = self.yosys_runner.synthesize(
                        verilog_files=design_input.verilog_files,
                        top_module=design_input.top_module,
                        workdir=workdir,
                        pdk=design_input.target_pdk,
                        liberty_path=liberty_path
                    )
                    record.synthesis_runtime_s = synth_result.runtime_s
                    record.artifacts["netlist_v"] = synth_result.artifact_paths.get("netlist_v", str(netlist_path))
                    record.raw_reports["yosys_log"] = synth_result.stdout_path
                    record.raw_reports["yosys_err"] = synth_result.stderr_path
                    break
                except (ToolExecutionError, ToolTimeoutError) as e:
                    attempt += 1
                    logger.warning(f"Synthesis attempt {attempt} failed: {e.message}")
                    if attempt > max_retries:
                        failure_stage = StageName.SYNTHESIS
                        error_summary = str(e)
                        record.status = RunStatus.FAILED
                        record.failure_stage = failure_stage
                        record.error_summary = error_summary
                        record.completed_at = _now()
                        record.total_runtime_s = round((record.completed_at - start_time).total_seconds(), 3)
                        self._persist_record(record)
                        return record

        # Aggregate synthesis metrics
        cell_hist = self.yosys_runner.parser.extract_cell_histogram(synth_metrics)
        record.cell_statistics = cell_hist
        for m in synth_metrics:
            if m.float_value is not None:
                all_metrics[m.name] = m.float_value

        # 3. Stage: OpenROAD Physical Design (if requested and configured)
        if run_physical_design:
            effective_pdk = pdk_config or {}
            try:
                p_result, p_metrics = self.openroad_runner.execute_flow(
                    design_input=design_input,
                    netlist_path=netlist_path,
                    workdir=workdir,
                    pdk_config=effective_pdk,
                    density=0.60
                )
                record.physical_design_runtime_s = p_result.runtime_s
                record.artifacts.update(p_result.artifact_paths)
                record.raw_reports["openroad_log"] = p_result.stdout_path
                record.raw_reports["openroad_err"] = p_result.stderr_path

                for m in p_metrics:
                    if m.float_value is not None:
                        all_metrics[m.name] = m.float_value
                    elif m.string_value:
                        all_metrics[m.name] = m.string_value
            except (ToolExecutionError, ToolTimeoutError) as e:
                logger.error(f"OpenROAD execution failed: {e.message}")
                failure_stage = StageName.ROUTING
                error_summary = str(e)
                record.status = RunStatus.FAILED
                record.failure_stage = failure_stage
                record.error_summary = error_summary

        # 4. Finalize status and metrics
        record.completed_at = _now()
        record.total_runtime_s = round((record.completed_at - start_time).total_seconds(), 3)
        record.metrics = all_metrics
        if failure_stage is None:
            record.status = RunStatus.COMPLETED

        # 5. Persist JSON & CSV experiment outputs
        self._persist_record(record)
        return record

    def _persist_record(self, record: ExperimentRecord):
        """Save structured JSON record in run dir and append row to master CSV."""
        run_dir = self.runs_dir / record.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # JSON record
        json_path = run_dir / "experiment_record.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))

        # Append to Master CSV
        csv_path = self.reports_dir / "master_experiments.csv"
        file_exists = csv_path.exists()

        flat_row = {
            "run_id": record.run_id,
            "design_name": record.design_name,
            "top_module": record.top_module,
            "status": record.status.value,
            "target_pdk": record.target_pdk,
            "clock_period_ns": record.clock_period_ns,
            "rtl_hash": record.rtl_hash[:12],
            "total_runtime_s": record.total_runtime_s,
            "synthesis_runtime_s": record.synthesis_runtime_s,
            "physical_design_runtime_s": record.physical_design_runtime_s,
            "total_cells": record.metrics.get("total_cells", 0),
            "chip_area_um2": record.metrics.get("chip_area_um2", 0.0),
            "wns": record.metrics.get("wns", ""),
            "tns": record.metrics.get("tns", ""),
            "total_power_w": record.metrics.get("total_power_w", ""),
            "total_wirelength_um": record.metrics.get("total_wirelength_um", ""),
            "failure_stage": record.failure_stage.value if record.failure_stage else "",
            "started_at": record.started_at.isoformat()
        }

        with open(csv_path, "a", newline="", encoding="utf-8") as cf:
            with self._csv_lock:
                writer = csv.DictWriter(cf, fieldnames=list(flat_row.keys()))
                if not file_exists:
                    writer.writeheader()
                writer.writerow(flat_row)

        logger.info(f"Persisted experiment record: {json_path} and updated {csv_path}")

    # ------------------------------------------------------------------ #
    #  Concurrent Experiment Execution (Step 5)                           #
    # ------------------------------------------------------------------ #

    _csv_lock = threading.Lock()  # serialize CSV appends across threads

    def execute_batch(
        self,
        designs: List[Tuple[DesignInput, Optional[Dict[str, Any]]]],
        run_physical_design: bool = False,
        max_workers: int = 2,
        max_retries: int = 1
    ) -> List[ExperimentRecord]:
        """Execute multiple designs concurrently with bounded thread pool.

        Args:
            designs: List of (DesignInput, pdk_config) tuples.
            run_physical_design: Whether to run OpenROAD PD flow per design.
            max_workers: Maximum concurrent synthesis/PD processes.
            max_retries: Per-design retry limit for transient failures.

        Returns:
            List of ExperimentRecord in submission order.
        """
        logger.info(
            f"Launching batch of {len(designs)} designs with max_workers={max_workers}"
        )
        results: List[Optional[ExperimentRecord]] = [None] * len(designs)

        def _run_one(idx: int, design_input: DesignInput, pdk_config):
            try:
                return idx, self.execute_flow(
                    design_input=design_input,
                    pdk_config=pdk_config,
                    run_physical_design=run_physical_design,
                    max_retries=max_retries
                )
            except Exception as exc:
                logger.error(
                    f"Batch design [{design_input.design_name}] raised exception: {exc}"
                )
                return idx, None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures: Dict[Future, int] = {}
            for i, (di, pdk_cfg) in enumerate(designs):
                fut = pool.submit(_run_one, i, di, pdk_cfg)
                futures[fut] = i

            for fut in as_completed(futures):
                idx, record = fut.result()
                results[idx] = record
                if record:
                    logger.info(
                        f"Batch [{record.design_name}] finished: {record.status.value} "
                        f"({record.total_runtime_s:.1f}s)"
                    )

        return [r for r in results if r is not None]

