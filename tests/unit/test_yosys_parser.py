"""Unit tests for Yosys log parsing and byte-offset provenance."""

import pytest
from pathlib import Path
from src.log_intelligence.yosys_parser import YosysLogParser


SAMPLE_YOSYS_LOG = """
=== alu ===

   Number of wires:                245
   Number of wire bits:            512
   Number of public wires:          48
   Number of public wire bits:     128
   Number of memories:               0
   Number of memory bits:            0
   Number of processes:              0
   Number of cells:                184
     $_AND_                         42
     $_OR_                          38
     $_XOR_                         24
     $_NOT_                         16
     $_MUX_                         64

Chip area for top module '\\alu': 1450.250000

Warning: Wire '\\alu.\\overflow' has no driver.
ERROR: Module '\\missing_sub' is not part of the current design.
"""


def test_yosys_log_parser(tmp_path):
    log_file = tmp_path / "sample_yosys.log"
    log_file.write_text(SAMPLE_YOSYS_LOG, encoding="utf-8")

    parser = YosysLogParser()
    metrics = parser.parse_file(log_file)

    metric_dict = {m.name: m for m in metrics}

    # Verify atomic metrics
    assert "total_cells" in metric_dict
    assert metric_dict["total_cells"].float_value == 184.0

    assert "num_wires" in metric_dict
    assert metric_dict["num_wires"].float_value == 245.0

    assert "chip_area_um2" in metric_dict
    assert metric_dict["chip_area_um2"].float_value == 1450.25

    # Verify individual cell breakdown
    hist = parser.extract_cell_histogram(metrics)
    assert hist["$_AND_"] == 42
    assert hist["$_OR_"] == 38
    assert hist["$_MUX_"] == 64

    # Verify event capture and byte offset provenance
    warnings = [m for m in metrics if m.name == "warning"]
    errors = [m for m in metrics if m.name == "error"]

    assert len(warnings) == 1
    assert "no driver" in warnings[0].string_value
    assert warnings[0].byte_offset > 0
    assert warnings[0].line_number > 0

    assert len(errors) == 1
    assert "missing_sub" in errors[0].string_value
