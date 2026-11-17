"""Integration test running real Yosys synthesis on verified benchmark designs."""

import pytest
from pathlib import Path
from src.common.types import DesignInput, RunStatus
from src.orchestration.flow_orchestrator import FlowOrchestrator


def test_real_yosys_synthesis_alu(tmp_path):
    alu_file = Path("benchmarks/alu/alu.v").resolve()
    assert alu_file.exists(), f"Benchmark design file not found: {alu_file}"

    design = DesignInput(
        design_name="integration_alu",
        top_module="alu",
        verilog_files=[alu_file],
        clock_period_ns=5.0
    )

    orchestrator = FlowOrchestrator(
        runs_dir=tmp_path / "runs",
        reports_dir=tmp_path / "reports",
        use_wsl=True
    )

    record = orchestrator.execute_flow(
        design_input=design,
        run_physical_design=False
    )

    # Assert real tool execution succeeded
    assert record.status == RunStatus.COMPLETED
    assert record.synthesis_runtime_s > 0.0
    assert record.metrics.get("total_cells", 0) > 0

    # Assert synthesized netlist artifact exists
    netlist_path = Path(record.artifacts["netlist_v"])
    assert netlist_path.exists()
    assert netlist_path.stat().st_size > 0

    # Assert raw log was preserved
    raw_log = Path(record.raw_reports["yosys_log"])
    assert raw_log.exists()
    assert raw_log.stat().st_size > 0

    # Assert cell distribution contains real primitive gates
    assert len(record.cell_statistics) > 0
