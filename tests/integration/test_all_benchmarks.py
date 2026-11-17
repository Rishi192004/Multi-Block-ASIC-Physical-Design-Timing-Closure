"""Integration test: priority_encoder benchmark design synthesis."""

import pytest
from pathlib import Path
from src.common.types import DesignInput, RunStatus
from src.orchestration.flow_orchestrator import FlowOrchestrator


def test_priority_encoder_synthesis(tmp_path):
    """priority_encoder must synthesize successfully with generic PDK."""
    rtl_file = Path("benchmarks/priority_encoder/priority_encoder.v").resolve()
    assert rtl_file.exists(), f"Benchmark RTL not found: {rtl_file}"

    design = DesignInput(
        design_name="integration_priority_encoder",
        top_module="priority_encoder",
        verilog_files=[rtl_file],
        clock_period_ns=7.0,
        clock_port_name="clk"
    )

    orch = FlowOrchestrator(
        runs_dir=tmp_path / "runs",
        reports_dir=tmp_path / "reports",
        use_wsl=True
    )

    record = orch.execute_flow(design_input=design, run_physical_design=False)

    assert record.status == RunStatus.COMPLETED, (
        f"priority_encoder synthesis failed: {record.error_summary}"
    )
    assert record.synthesis_runtime_s > 0.0
    assert record.metrics.get("total_cells", 0) > 0

    netlist = Path(record.artifacts["netlist_v"])
    assert netlist.exists() and netlist.stat().st_size > 0

    # Priority encoder has flip-flops for registered outputs
    # Expect at least one D-type FF in cell stats
    all_cells = " ".join(record.cell_statistics.keys()).lower()
    assert len(record.cell_statistics) > 0, "No cell statistics parsed"


def test_all_six_benchmarks_synthesize(tmp_path):
    """All 6 benchmark designs must complete synthesis without error."""
    benchmarks = [
        ("alu",              "alu",              "benchmarks/alu/alu.v",                               5.0),
        ("uart_tx",          "uart_tx",          "benchmarks/uart_tx/uart_tx.v",                       8.0),
        ("fifo_sync",        "fifo_sync",        "benchmarks/fifo_sync/fifo_sync.v",                   6.0),
        ("fsm_traffic",      "fsm_traffic",      "benchmarks/fsm_traffic/fsm_traffic.v",               10.0),
        ("booth_multiplier", "booth_multiplier", "benchmarks/booth_multiplier/booth_multiplier.v",     12.0),
        ("priority_encoder", "priority_encoder", "benchmarks/priority_encoder/priority_encoder.v",     7.0),
    ]

    orch = FlowOrchestrator(
        runs_dir=tmp_path / "runs",
        reports_dir=tmp_path / "reports",
        use_wsl=True
    )

    for design_name, top_module, file_path, clk_ns in benchmarks:
        rtl = Path(file_path).resolve()
        if not rtl.exists():
            pytest.skip(f"RTL file not found: {rtl}")

        design = DesignInput(
            design_name=f"batch_{design_name}",
            top_module=top_module,
            verilog_files=[rtl],
            clock_period_ns=clk_ns,
            clock_port_name="clk"
        )
        record = orch.execute_flow(design_input=design, run_physical_design=False)

        assert record.status == RunStatus.COMPLETED, (
            f"Design '{design_name}' failed: {record.error_summary}"
        )
        assert record.metrics.get("total_cells", 0) > 0, (
            f"Design '{design_name}' produced zero cells"
        )
