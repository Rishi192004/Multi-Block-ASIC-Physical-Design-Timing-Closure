"""
Integration test: sky130hd Yosys synthesis — verify mapped cell names.
"""
import os
import pytest
from pathlib import Path
from src.orchestration.yosys_runner import YosysRunner
from src.orchestration.tool_runner import ToolRunner

YOSYS_OK = Path("/usr/bin/yosys").exists()
PDK_LIB  = Path("/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")
SYMLINK_OK = Path("/opt/cad_ai").exists()

skip_conds = []
if not YOSYS_OK:
    skip_conds.append("yosys not found")
if not PDK_LIB.exists():
    skip_conds.append("sky130A liberty not found")
if not SYMLINK_OK:
    skip_conds.append("/opt/cad_ai symlink missing")

PROJECT_ROOT = Path("/opt/cad_ai") if SYMLINK_OK else Path.cwd()
ALU_RTL  = PROJECT_ROOT / "benchmarks" / "alu" / "alu.v"
RUNS_DIR = PROJECT_ROOT / "artifacts" / "runs"


@pytest.mark.skipif(len(skip_conds) > 0, reason="; ".join(skip_conds))
class TestYosysSky130Synthesis:
    def setup_method(self):
        runner = ToolRunner(use_wsl=False)
        self.yosys = YosysRunner(runner=runner, yosys_binary="/usr/bin/yosys")

    def test_sky130hd_synthesis_runs(self, tmp_path):
        """sky130hd synthesis with liberty must succeed (exit code 0)."""
        result, metrics = self.yosys.synthesize(
            verilog_files=[ALU_RTL],
            top_module="alu",
            workdir=tmp_path,
            pdk="sky130hd",
            liberty_path=str(PDK_LIB),
        )
        assert result.exit_code == 0, f"Yosys sky130hd synthesis failed:\n{result.stderr_path}"

    def test_sky130hd_produces_mapped_cells(self, tmp_path):
        """sky130hd synthesis must produce at least one sky130_fd_sc_hd cell."""
        result, metrics = self.yosys.synthesize(
            verilog_files=[ALU_RTL],
            top_module="alu",
            workdir=tmp_path,
            pdk="sky130hd",
            liberty_path=str(PDK_LIB),
        )
        assert result.exit_code == 0
        cell_names = [m.name for m in metrics]
        sky130_cells = [n for n in cell_names if "sky130_fd_sc_hd" in n]
        assert len(sky130_cells) > 0, (
            f"Expected sky130 mapped cells. Metrics found: {cell_names[:20]}"
        )

    def test_generic_synthesis_runs(self, tmp_path):
        """Generic (non-PDK) synthesis must still work after sky130 path is added."""
        result, metrics = self.yosys.synthesize(
            verilog_files=[ALU_RTL],
            top_module="alu",
            workdir=tmp_path,
            pdk="generic",
        )
        assert result.exit_code == 0

    def test_netlist_file_written(self, tmp_path):
        """Synthesis must write a non-empty _synth.v netlist file."""
        result, _ = self.yosys.synthesize(
            verilog_files=[ALU_RTL],
            top_module="alu",
            workdir=tmp_path,
            pdk="sky130hd",
            liberty_path=str(PDK_LIB),
        )
        assert result.exit_code == 0
        netlist = tmp_path / "alu_synth.v"
        assert netlist.exists(), "Synthesized netlist file not written"
        assert netlist.stat().st_size > 100, "Netlist file is suspiciously small"
