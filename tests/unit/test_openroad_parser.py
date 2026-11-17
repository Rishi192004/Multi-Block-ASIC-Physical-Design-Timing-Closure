"""Unit tests for OpenROAD timing, area, and power log parsing."""

import pytest
from pathlib import Path
from src.log_intelligence.openroad_parser import OpenROADLogParser


SAMPLE_TIMING_REPORT = """
===========================================================================
report_checks -path_delay min_max
===========================================================================
Startpoint: r_reg[0] (rising edge-triggered flip-flop clocked by core_clock)
Endpoint: out_port[0] (output port clocked by core_clock)
Path Group: core_clock
Path Type: max

  Delay    Time   Description
---------------------------------------------------------
   0.00    0.00   clock core_clock (rise edge)
   0.15    0.15   clock network delay (ideal)
   0.20    0.35 ^ r_reg[0]/CLK (sky130_fd_sc_hd__dfxtp_1)
   0.45    0.80 ^ r_reg[0]/Q (sky130_fd_sc_hd__dfxtp_1)
   1.20    2.00 ^ out_port[0] (out)
           2.00   data arrival time

  10.00   10.00   clock core_clock (rise edge)
  -0.25    9.75   clock uncertainty
   0.00    9.75   clock reconvergence pessimism
  -2.00    7.75   output delay
           7.75   data required time
---------------------------------------------------------
           7.75   data required time
          -2.00   data arrival time
---------------------------------------------------------
           5.75   slack (MET)

worst slack 5.75
tns 0.00
"""

SAMPLE_OPENROAD_LOG = """
[INFO ODB-0130] Initializing floorplan...
[INFO ODB-0131] Core area: 10.0 10.0 110.0 110.0
[INFO ODB-0132] Die area: 0.0 0.0 120.0 120.0
Design area 4520.50 u^2 45.2% utilization.
Total wire length: 12543.80 um
Total number of overflowed GCells: 0
Found 0 DRC violations
"""

SAMPLE_POWER_REPORT = """
===========================================================================
report_power
===========================================================================
Group                  Internal  Switching    Leakage      Total
---------------------------------------------------------------------------
Sequential              1.25e-04   4.20e-05   1.12e-08   1.67e-04
Combinational           3.40e-04   1.80e-04   2.45e-08   5.20e-04
Total                   4.65e-04   2.22e-04   3.57e-08   6.87e-04
"""


def test_openroad_timing_parser(tmp_path):
    rpt_file = tmp_path / "timing.rpt"
    rpt_file.write_text(SAMPLE_TIMING_REPORT, encoding="utf-8")

    parser = OpenROADLogParser()
    metrics = parser.parse_timing_report(rpt_file)
    m_dict = {m.name: m for m in metrics}

    assert "wns" in m_dict
    assert m_dict["wns"].float_value == 5.75
    assert "tns" in m_dict
    assert m_dict["tns"].float_value == 0.00
    assert "worst_slack" in m_dict
    assert m_dict["worst_slack"].float_value == 5.75
    assert m_dict["worst_slack"].string_value == "MET"


def test_openroad_log_parser(tmp_path):
    log_file = tmp_path / "openroad.log"
    log_file.write_text(SAMPLE_OPENROAD_LOG, encoding="utf-8")

    parser = OpenROADLogParser()
    metrics = parser.parse_log_file(log_file)
    m_dict = {m.name: m for m in metrics}

    assert "design_area_um2" in m_dict
    assert m_dict["design_area_um2"].float_value == 4520.50
    assert "core_utilization_pct" in m_dict
    assert m_dict["core_utilization_pct"].float_value == 45.2
    assert "total_wirelength_um" in m_dict
    assert m_dict["total_wirelength_um"].float_value == 12543.80
    assert "grc_overflow_cells" in m_dict
    assert m_dict["grc_overflow_cells"].float_value == 0.0
    assert "drc_violations" in m_dict
    assert m_dict["drc_violations"].float_value == 0.0


def test_openroad_power_parser(tmp_path):
    pwr_file = tmp_path / "power.rpt"
    pwr_file.write_text(SAMPLE_POWER_REPORT, encoding="utf-8")

    parser = OpenROADLogParser()
    metrics = parser.parse_power_report(pwr_file)
    m_dict = {m.name: m for m in metrics}

    assert "total_power_w" in m_dict
    assert pytest.approx(m_dict["total_power_w"].float_value, 1e-6) == 6.87e-04
    assert pytest.approx(m_dict["leakage_power_w"].float_value, 1e-9) == 3.57e-08
