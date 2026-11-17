"""Physical design configuration and constraints feature extractor."""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PDConfigFeatures(BaseModel):
    """Structured container for physical-design configuration features."""
    pd_target_utilization: float = 0.50
    pd_core_aspect_ratio: float = 1.0
    pd_core_space_um: float = 10.0
    pd_clock_period_ns: float = 10.0
    pd_clock_uncertainty_ns: float = 0.25
    pd_clock_transition_ns: float = 0.15
    pd_num_routing_layers: int = 6
    pd_target_pdk: str = "generic"
    pd_is_sky130: bool = False


class ConfigExtractor:
    """Parses SDC constraints, floorplan parameters, and PDK configuration."""

    def __init__(self):
        self.re_clock = re.compile(r"create_clock\s+.*?-period\s+([0-9\.]+)")
        self.re_uncertainty = re.compile(r"set_clock_uncertainty\s+([0-9\.]+)")
        self.re_transition = re.compile(r"set_clock_transition\s+([0-9\.]+)")
        self.re_floorplan = re.compile(
            r"initialize_floorplan\s+.*?-utilization\s+([0-9\.]+)\s+.*?-aspect_ratio\s+([0-9\.]+)\s+.*?-core_space\s+([0-9\.]+)"
        )

    def extract_from_run(
        self,
        run_record: Dict[str, Any],
        workdir: Optional[Path] = None
    ) -> PDConfigFeatures:
        """Extract configuration features from run record dict and optional workdir files."""
        pdk = run_record.get("target_pdk", "generic")
        clock_period = float(run_record.get("clock_period_ns", 10.0))
        is_sky130 = (pdk == "sky130hd")
        num_layers = 6 if is_sky130 else 0

        utilization = 0.50
        aspect_ratio = 1.0
        core_space = 10.0
        uncertainty = 0.25
        transition = 0.15

        # Inspect SDC file if present
        if workdir and workdir.exists():
            sdc_files = list(workdir.glob("*.sdc"))
            if sdc_files:
                sdc_text = sdc_files[0].read_text(encoding="utf-8", errors="replace")
                m_clk = self.re_clock.search(sdc_text)
                if m_clk:
                    clock_period = float(m_clk.group(1))
                m_unc = self.re_uncertainty.search(sdc_text)
                if m_unc:
                    uncertainty = float(m_unc.group(1))
                m_trn = self.re_transition.search(sdc_text)
                if m_trn:
                    transition = float(m_trn.group(1))

            # Inspect flow.tcl if present for floorplan settings
            flow_tcl = workdir / "flow.tcl"
            if flow_tcl.exists():
                tcl_text = flow_tcl.read_text(encoding="utf-8", errors="replace")
                m_fp = self.re_floorplan.search(tcl_text)
                if m_fp:
                    utilization = float(m_fp.group(1)) / 100.0 if float(m_fp.group(1)) > 1.0 else float(m_fp.group(1))
                    aspect_ratio = float(m_fp.group(2))
                    core_space = float(m_fp.group(3))

        return PDConfigFeatures(
            pd_target_utilization=utilization,
            pd_core_aspect_ratio=aspect_ratio,
            pd_core_space_um=core_space,
            pd_clock_period_ns=clock_period,
            pd_clock_uncertainty_ns=uncertainty,
            pd_clock_transition_ns=transition,
            pd_num_routing_layers=num_layers,
            pd_target_pdk=pdk,
            pd_is_sky130=is_sky130
        )
