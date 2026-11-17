"""
Integration test: Full sky130hd RTL→synthesis→placement pipeline on uart_tx.

Requires:
  - Yosys 0.9 at /usr/bin/yosys (WSL Ubuntu-22.04)
  - OpenROAD at /opt/eda_env/bin/openroad
  - Sky130A PDK at /opt/eda_env/share/pdk/sky130A/
  - /opt/cad_ai symlink to project root (created by setup script)

Skip marker: set env var SKIP_PD_TEST=1 to skip in CI environments without tools.
"""

import os
import pytest
from pathlib import Path
from src.orchestration.flow_orchestrator import FlowOrchestrator
from src.common.types import DesignInput, RunStatus

# ---------------------------------------------------------------------------
# Skip guard — physical design is slow and tool-dependent
# ---------------------------------------------------------------------------
SKIP_PD = os.environ.get("SKIP_PD_TEST", "0") == "1"
YOSYS_OK = Path("/usr/bin/yosys").exists()
OR_OK = Path("/opt/eda_env/bin/openroad").exists()
PDK_LIB = Path("/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")
SYMLINK_OK = Path("/opt/cad_ai").exists()

skip_reason = []
if SKIP_PD:
    skip_reason.append("SKIP_PD_TEST=1")
if not YOSYS_OK:
    skip_reason.append("yosys not found at /usr/bin/yosys")
if not OR_OK:
    skip_reason.append("openroad not found at /opt/eda_env/bin/openroad")
if not PDK_LIB.exists():
    skip_reason.append("sky130A liberty not found")
if not SYMLINK_OK:
    skip_reason.append("/opt/cad_ai symlink missing (run: ln -sfn '/mnt/c/Users/Lenovo/Desktop/CAD_AI PROJEC' /opt/cad_ai)")

TOOLS_AVAILABLE = len(skip_reason) == 0


PDK_CONFIG = {
    "tech_lef":    "/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef",
    "std_cell_lef":"/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef",
    "liberty_file":str(PDK_LIB),
}

PROJECT_ROOT = Path("/opt/cad_ai") if SYMLINK_OK else Path.cwd()
RUNS_DIR  = PROJECT_ROOT / "artifacts" / "runs"
RPT_DIR   = PROJECT_ROOT / "artifacts" / "reports"
UART_RTL  = PROJECT_ROOT / "benchmarks" / "uart_tx" / "uart_tx.v"


@pytest.mark.skipif(not TOOLS_AVAILABLE, reason="; ".join(skip_reason) or "Tools not available")
class TestOpenROADPlacement:
    """End-to-end physical design integration tests using sky130hd PDK."""

    def setup_method(self):
        self.orchestrator = FlowOrchestrator(
            runs_dir=RUNS_DIR,
            reports_dir=RPT_DIR,
            yosys_binary="/usr/bin/yosys",
            openroad_binary="/opt/eda_env/bin/openroad",
            use_wsl=False,  # running directly inside WSL
        )
        self.design = DesignInput(
            design_name="uart_tx_pd_test",
            top_module="uart_tx",
            verilog_files=[UART_RTL],
            target_pdk="sky130hd",
            clock_period_ns=10.0,
            clock_port_name="clk",
            core_utilization=0.40,
            aspect_ratio=1.0,
        )

    def test_full_pd_flow_completes(self):
        """Full RTL→synthesis→placement flow must complete with status COMPLETED."""
        record = self.orchestrator.execute_flow(
            design_input=self.design,
            pdk_config=PDK_CONFIG,
            run_physical_design=True,
        )
        assert record.status == RunStatus.COMPLETED, (
            f"Flow did not complete. Status={record.status}, error={record.error_summary}"
        )

    def test_synthesis_produces_sky130_cells(self):
        """Yosys with sky130hd+liberty must produce mapped sky130_fd_sc_hd__* cells."""
        record = self.orchestrator.execute_flow(
            design_input=self.design,
            pdk_config=PDK_CONFIG,
            run_physical_design=False,
        )
        assert record.status == RunStatus.COMPLETED
        # At least some cells should be sky130-mapped
        cell_stats = record.cell_statistics
        sky130_cells = [k for k in cell_stats if "sky130_fd_sc_hd" in k]
        assert len(sky130_cells) > 0, (
            f"No sky130 cells found in cell_statistics. Got: {list(cell_stats.keys())[:10]}"
        )

    def test_def_file_produced(self):
        """OpenROAD placement must write a non-empty DEF file."""
        record = self.orchestrator.execute_flow(
            design_input=self.design,
            pdk_config=PDK_CONFIG,
            run_physical_design=True,
        )
        assert record.status == RunStatus.COMPLETED
        def_path = record.artifacts.get("def")
        assert def_path is not None, "DEF artifact path not recorded in experiment record"
        assert Path(def_path).exists(), f"DEF file does not exist: {def_path}"
        assert Path(def_path).stat().st_size > 1024, "DEF file is suspiciously small"

    def test_design_area_extracted(self):
        """OpenROAD log must yield a positive design area metric."""
        record = self.orchestrator.execute_flow(
            design_input=self.design,
            pdk_config=PDK_CONFIG,
            run_physical_design=True,
        )
        assert record.status == RunStatus.COMPLETED
        area = record.metrics.get("chip_area_um2") or record.metrics.get("design_area_um2")
        assert area is not None, f"design area not found in metrics. Keys: {list(record.metrics.keys())}"
        assert float(area) > 0.0, f"design area must be positive, got {area}"

    def test_timing_report_produced(self):
        """OpenROAD must generate a non-empty timing signoff report."""
        record = self.orchestrator.execute_flow(
            design_input=self.design,
            pdk_config=PDK_CONFIG,
            run_physical_design=True,
        )
        assert record.status == RunStatus.COMPLETED
        timing_path = record.artifacts.get("timing_rpt")
        assert timing_path is not None, "timing_rpt artifact not recorded"
        assert Path(timing_path).exists(), f"Timing report does not exist: {timing_path}"
        assert Path(timing_path).stat().st_size > 100, "Timing report is empty"
