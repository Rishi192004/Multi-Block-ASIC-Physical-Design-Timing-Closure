"""OpenROAD runner with correct sky130hd flow configuration."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from src.common.types import ExecutionResult, ToolType, StageName, ParsedMetric, DesignInput
from src.common.exceptions import ConfigurationError, ToolExecutionError
from src.orchestration.tool_runner import ToolRunner
from src.log_intelligence.openroad_parser import OpenROADLogParser
from src.common.logger import logger

SKY130_TRACKS = """
make_tracks li1  -x_offset 0.23 -x_pitch 0.46 -y_offset 0.17 -y_pitch 0.34
make_tracks met1 -x_offset 0.17 -x_pitch 0.34 -y_offset 0.17 -y_pitch 0.34
make_tracks met2 -x_offset 0.23 -x_pitch 0.46 -y_offset 0.23 -y_pitch 0.46
make_tracks met3 -x_offset 0.34 -x_pitch 0.68 -y_offset 0.34 -y_pitch 0.68
make_tracks met4 -x_offset 0.46 -x_pitch 0.92 -y_offset 0.46 -y_pitch 0.92
make_tracks met5 -x_offset 1.70 -x_pitch 3.40 -y_offset 1.70 -y_pitch 3.40
"""


class OpenROADRunner:
    def __init__(self, runner: Optional[ToolRunner] = None,
                 openroad_binary: str = "/opt/eda_env/bin/openroad"):
        self.runner = runner or ToolRunner()
        self.binary = openroad_binary
        self.parser = OpenROADLogParser()

    def generate_sdc(self, clock_port: str, clock_period_ns: float,
                     output_sdc_path: Path, has_clock: bool = True) -> Path:
        """Generate SDC timing constraints.

        For combinational designs (has_clock=False) only I/O delay constraints
        are emitted referenced to a virtual clock so OpenSTA can still perform
        static timing analysis without a real clock port.
        """
        sdc = []
        if has_clock:
            sdc += [
                f"create_clock -name core_clock -period {clock_period_ns} [get_ports {clock_port}]",
                f"set_clock_uncertainty 0.25 [get_clocks core_clock]",
                f"set_clock_transition 0.15 [get_clocks core_clock]",
                # OpenSTA compatible: remove -no_clocks flag
                f"set_input_delay  -clock core_clock {clock_period_ns * 0.2:.3f} [all_inputs]",
                f"set_output_delay -clock core_clock {clock_period_ns * 0.2:.3f} [all_outputs]",
            ]
        else:
            # Virtual clock for combinational-only design
            sdc += [
                f"create_clock -name virt_clock -period {clock_period_ns}",
                f"set_input_delay  -clock virt_clock {clock_period_ns * 0.2:.3f} [all_inputs]",
                f"set_output_delay -clock virt_clock {clock_period_ns * 0.2:.3f} [all_outputs]",
            ]
        with open(output_sdc_path, "w") as f:
            f.write("\n".join(sdc) + "\n")
        return output_sdc_path

    def generate_flow_tcl(self, design_input: DesignInput, netlist_path: Path,
                          sdc_path: Path, pdk_config: Dict[str, Any],
                          workdir: Path, density: float = 0.60) -> str:
        top = design_input.top_module
        pdk = design_input.target_pdk
        tech_lef = pdk_config.get("tech_lef", "")
        std_lef  = pdk_config.get("std_cell_lef", "")
        liberty  = pdk_config.get("liberty_file", "")
        is_sky130 = (pdk == "sky130hd")

        netlist_wsl = self.runner._convert_path(netlist_path)
        sdc_wsl     = self.runner._convert_path(sdc_path)
        timing_rpt  = self.runner._convert_path(workdir / "timing_signoff.rpt")
        power_rpt   = self.runner._convert_path(workdir / "power_signoff.rpt")
        def_out     = self.runner._convert_path(workdir / f"{top}_placed.def")

        lines = [
            f"# OpenROAD PD Script for {top} — {pdk} — EDA-Genius",
            f'read_lef "{tech_lef}"',
            f'read_lef "{std_lef}"',
            f'read_liberty "{liberty}"',
            f'read_verilog "{netlist_wsl}"',
            f"link_design {top}",
            f'read_sdc "{sdc_wsl}"',
            "",
            f"# Floorplan",
            f'initialize_floorplan -site unithd -utilization 40 -aspect_ratio 1.0 -core_space 10.0',
        ]

        if is_sky130:
            lines.append(SKY130_TRACKS)

        lines += [
            "place_pins -hor_layers met3 -ver_layers met2",
            "",
            "# Global + Detailed Placement",
            f"global_placement -density {density}",
            "detailed_placement",
            "",
            "# Signoff Reports",
            f'report_design_area > "{timing_rpt}"',
            f'report_checks -path_delay min_max -digits 4 >> "{timing_rpt}"',
            f'report_worst_slack -max >> "{timing_rpt}"',
            f'report_tns >> "{timing_rpt}"',
            f'report_power > "{power_rpt}"',
            "",
            f'write_def "{def_out}"',
            "exit"
        ]
        return "\n".join(lines) + "\n"

    def _has_clock_port(self, netlist_path: Path, clock_port: str) -> bool:
        """Scan synthesized netlist to check if the top module has the given clock port."""
        try:
            text = netlist_path.read_text(errors="replace")
            # Look for the port declaration, e.g. "input clk" or "input wire clk"
            import re
            return bool(re.search(rf'\binput\b[^;]*\b{re.escape(clock_port)}\b', text))
        except Exception:
            return True  # assume clock present if we can't read the file

    def execute_flow(self, design_input: DesignInput, netlist_path: Path,
                     workdir: Path, pdk_config: Dict[str, Any],
                     density: float = 0.60, timeout_s: int = 3600
                     ) -> Tuple[ExecutionResult, List[ParsedMetric]]:
        workdir.mkdir(parents=True, exist_ok=True)
        top = design_input.top_module

        sdc_path = workdir / f"{top}.sdc"
        has_clk = self._has_clock_port(netlist_path, design_input.clock_port_name)
        self.generate_sdc(design_input.clock_port_name, design_input.clock_period_ns,
                          sdc_path, has_clock=has_clk)

        tcl_path = workdir / "flow.tcl"
        with open(tcl_path, "w") as f:
            f.write(self.generate_flow_tcl(design_input, netlist_path, sdc_path,
                                           pdk_config, workdir, density))

        stdout_path = workdir / "openroad.log"
        stderr_path = workdir / "openroad.err"
        tcl_wsl = self.runner._convert_path(tcl_path)
        command = [self.binary, "-exit", tcl_wsl]

        result = self.runner.execute(
            command=command, workdir=workdir,
            stdout_path=stdout_path, stderr_path=stderr_path,
            tool=ToolType.OPENROAD, stage=StageName.PLACEMENT,
            timeout_s=timeout_s
        )

        for art, fname in [("def", f"{top}_placed.def"),
                           ("timing_rpt", "timing_signoff.rpt"),
                           ("power_rpt", "power_signoff.rpt")]:
            p = workdir / fname
            if p.exists():
                result.artifact_paths[art] = str(p.resolve())

        metrics: List[ParsedMetric] = []
        metrics.extend(self.parser.parse_log_file(stdout_path))
        timing_f = workdir / "timing_signoff.rpt"
        if timing_f.exists():
            metrics.extend(self.parser.parse_timing_report(timing_f))
        power_f = workdir / "power_signoff.rpt"
        if power_f.exists():
            metrics.extend(self.parser.parse_power_report(power_f))

        return result, metrics
