"""Parser for OpenROAD physical design logs and signoff reports."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.common.types import ParsedMetric
from src.common.logger import logger


class OpenROADLogParser:
    """Parses OpenROAD execution logs, OpenSTA timing reports, and power reports."""

    def __init__(self):
        # OpenSTA timing report patterns
        self.re_wns = re.compile(r"worst slack\s+([-\d\.]+)")
        self.re_tns = re.compile(r"tns\s+([-\d\.]+)")
        self.re_slack = re.compile(r"([-\d\.]+)\s+slack\s+\((VIOLATED|MET)\)|slack\s+\((VIOLATED|MET)\)\s+([-\d\.]+)")
        self.re_data_arrival = re.compile(r"^\s*([\d\.]+)\s+data arrival time")
        self.re_data_required = re.compile(r"^\s*([\d\.]+)\s+data required time")

        # OpenROAD area and utilization patterns
        self.re_die_area = re.compile(r"Die area:\s+([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+)")
        self.re_core_area = re.compile(r"Core area:\s+([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+)")
        self.re_design_area = re.compile(r"Design area\s+([0-9\.]+)\s+u\^2\s+([0-9\.]+)%\s+utilization")
        self.re_utilization = re.compile(r"utilization:\s+([0-9\.]+)%")

        # Congestion and routing patterns
        self.re_grc_overflow = re.compile(r"Total number of overflowed GCells:\s+(\d+)")
        self.re_wirelength = re.compile(r"Total wire length:\s+([0-9\.]+)\s*(um|m)?")
        self.re_drc_violations = re.compile(r"Found\s+(\d+)\s+DRC violations")

        # Power report patterns
        self.re_total_power = re.compile(r"Total\s+([0-9\.eE+-]+)\s+([0-9\.eE+-]+)\s+([0-9\.eE+-]+)\s+([0-9\.eE+-]+)")
        self.re_power_mw = re.compile(r"Total Power\s+=\s+([0-9\.eE+-]+)\s*(mW|W|uW)?")

    def parse_timing_report(self, report_path: Path) -> List[ParsedMetric]:
        """Extract WNS, TNS, and timing slack from OpenSTA report."""
        if not report_path.exists():
            return []

        metrics: List[ParsedMetric] = []
        byte_offset = 0

        with open(report_path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                raw_line = line.rstrip("\r\n")

                m_wns = self.re_wns.search(raw_line)
                if m_wns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="wns",
                        float_value=float(m_wns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                m_tns = self.re_tns.search(raw_line)
                if m_tns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="tns",
                        float_value=float(m_tns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                m_slack = self.re_slack.search(raw_line)
                if m_slack:
                    if m_slack.group(1):
                        val = float(m_slack.group(1))
                        status = m_slack.group(2)
                    else:
                        status = m_slack.group(3)
                        val = float(m_slack.group(4))
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="worst_slack",
                        float_value=val,
                        string_value=status,
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Timing metrics from log (fallback / primary)
                m_wns = self.re_wns.search(raw_line)
                if m_wns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="wns",
                        float_value=float(m_wns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                m_tns = self.re_tns.search(raw_line)
                if m_tns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="tns",
                        float_value=float(m_tns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Power from log (fallback / primary)
                m_tp = self.re_total_power.search(raw_line)
                if m_tp:
                    total_pwr = float(m_tp.group(4))
                    metrics.append(ParsedMetric(
                        category="POWER",
                        name="total_power_w",
                        float_value=total_pwr,
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                byte_offset += len(line.encode("utf-8"))

        return metrics

    def parse_log_file(self, log_path: Path) -> List[ParsedMetric]:
        """Extract area, utilization, congestion, wirelength, and DRC from main OpenROAD log."""
        if not log_path.exists():
            return []

        metrics: List[ParsedMetric] = []
        byte_offset = 0

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                raw_line = line.rstrip("\r\n")

                # Design area & utilization
                m_des_area = self.re_design_area.search(raw_line)
                if m_des_area:
                    metrics.append(ParsedMetric(
                        category="AREA",
                        name="design_area_um2",
                        float_value=float(m_des_area.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))
                    metrics.append(ParsedMetric(
                        category="AREA",
                        name="core_utilization_pct",
                        float_value=float(m_des_area.group(2)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # GRC Overflow
                m_grc = self.re_grc_overflow.search(raw_line)
                if m_grc:
                    metrics.append(ParsedMetric(
                        category="CONGESTION",
                        name="grc_overflow_cells",
                        float_value=float(m_grc.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Wire length
                m_wl = self.re_wirelength.search(raw_line)
                if m_wl:
                    val = float(m_wl.group(1))
                    unit = m_wl.group(2) or "um"
                    if unit == "m":
                        val *= 1e6
                    metrics.append(ParsedMetric(
                        category="ROUTING",
                        name="total_wirelength_um",
                        float_value=val,
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # DRC violations
                m_drc = self.re_drc_violations.search(raw_line)
                if m_drc:
                    metrics.append(ParsedMetric(
                        category="ROUTING",
                        name="drc_violations",
                        float_value=float(m_drc.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Timing metrics from log (fallback / primary)
                m_wns = self.re_wns.search(raw_line)
                if m_wns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="wns",
                        float_value=float(m_wns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                m_tns = self.re_tns.search(raw_line)
                if m_tns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="tns",
                        float_value=float(m_tns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Power from log (fallback / primary)
                m_tp = self.re_total_power.search(raw_line)
                if m_tp:
                    total_pwr = float(m_tp.group(4))
                    metrics.append(ParsedMetric(
                        category="POWER",
                        name="total_power_w",
                        float_value=total_pwr,
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                byte_offset += len(line.encode("utf-8"))

        return metrics

    def parse_power_report(self, report_path: Path) -> List[ParsedMetric]:
        """Extract internal, switching, leakage, and total power from power report."""
        if not report_path.exists():
            return []

        metrics: List[ParsedMetric] = []
        byte_offset = 0

        with open(report_path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                raw_line = line.rstrip("\r\n")

                m_tot = self.re_total_power.search(raw_line)
                if m_tot:
                    # Format: Internal, Switching, Leakage, Total
                    try:
                        metrics.append(ParsedMetric(
                            category="POWER",
                            name="internal_power_w",
                            float_value=float(m_tot.group(1)),
                            line_number=line_no,
                            byte_offset=byte_offset,
                            raw_snippet=raw_line
                        ))
                        metrics.append(ParsedMetric(
                            category="POWER",
                            name="switching_power_w",
                            float_value=float(m_tot.group(2)),
                            line_number=line_no,
                            byte_offset=byte_offset,
                            raw_snippet=raw_line
                        ))
                        metrics.append(ParsedMetric(
                            category="POWER",
                            name="leakage_power_w",
                            float_value=float(m_tot.group(3)),
                            line_number=line_no,
                            byte_offset=byte_offset,
                            raw_snippet=raw_line
                        ))
                        metrics.append(ParsedMetric(
                            category="POWER",
                            name="total_power_w",
                            float_value=float(m_tot.group(4)),
                            line_number=line_no,
                            byte_offset=byte_offset,
                            raw_snippet=raw_line
                        ))
                    except ValueError:
                        pass

                # Timing metrics from log (fallback / primary)
                m_wns = self.re_wns.search(raw_line)
                if m_wns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="wns",
                        float_value=float(m_wns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                m_tns = self.re_tns.search(raw_line)
                if m_tns:
                    metrics.append(ParsedMetric(
                        category="TIMING",
                        name="tns",
                        float_value=float(m_tns.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Power from log (fallback / primary)
                m_tp = self.re_total_power.search(raw_line)
                if m_tp:
                    total_pwr = float(m_tp.group(4))
                    metrics.append(ParsedMetric(
                        category="POWER",
                        name="total_power_w",
                        float_value=total_pwr,
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                byte_offset += len(line.encode("utf-8"))

        return metrics
