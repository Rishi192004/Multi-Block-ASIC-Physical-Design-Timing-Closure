"""Unit tests for RTL input management and validation."""

import pytest
from pathlib import Path
from src.common.types import DesignInput
from src.common.exceptions import ConfigurationError, RTLValidationError
from src.orchestration.flow_orchestrator import FlowOrchestrator


def test_validate_rtl_inputs_success(tmp_path):
    verilog_file = tmp_path / "sample.v"
    verilog_file.write_text("module sample(input clk, output reg q); endmodule")

    design = DesignInput(
        design_name="sample_test",
        top_module="sample",
        verilog_files=[verilog_file],
        clock_period_ns=5.0
    )

    orchestrator = FlowOrchestrator(runs_dir=tmp_path / "runs", reports_dir=tmp_path / "reports")
    # Should not raise
    orchestrator.validate_rtl_inputs(design)


def test_validate_rtl_missing_file(tmp_path):
    non_existent = tmp_path / "ghost.v"
    design = DesignInput(
        design_name="sample_ghost",
        top_module="sample",
        verilog_files=[non_existent]
    )

    orchestrator = FlowOrchestrator(runs_dir=tmp_path / "runs", reports_dir=tmp_path / "reports")
    with pytest.raises(RTLValidationError, match="not found"):
        orchestrator.validate_rtl_inputs(design)


def test_validate_rtl_invalid_extension(tmp_path):
    bad_ext = tmp_path / "sample.txt"
    bad_ext.write_text("some text")

    design = DesignInput(
        design_name="sample_bad_ext",
        top_module="sample",
        verilog_files=[bad_ext]
    )

    orchestrator = FlowOrchestrator(runs_dir=tmp_path / "runs", reports_dir=tmp_path / "reports")
    with pytest.raises(RTLValidationError, match="Invalid RTL extension"):
        orchestrator.validate_rtl_inputs(design)


def test_validate_rtl_invalid_top_module(tmp_path):
    v_file = tmp_path / "sample.v"
    v_file.write_text("module sample(); endmodule")

    design = DesignInput(
        design_name="sample_bad_top",
        top_module="123_invalid_id!",
        verilog_files=[v_file]
    )

    orchestrator = FlowOrchestrator(runs_dir=tmp_path / "runs", reports_dir=tmp_path / "reports")
    with pytest.raises(RTLValidationError, match="Invalid top module name identifier"):
        orchestrator.validate_rtl_inputs(design)


def test_rtl_hashing_consistency(tmp_path):
    f1 = tmp_path / "a.v"
    f2 = tmp_path / "b.v"
    f1.write_text("module a; endmodule")
    f2.write_text("module b; endmodule")

    orchestrator = FlowOrchestrator(runs_dir=tmp_path / "runs", reports_dir=tmp_path / "reports")
    hash1 = orchestrator.compute_rtl_hash([f1, f2])
    hash2 = orchestrator.compute_rtl_hash([f2, f1])  # Order-independent due to sorting

    assert hash1 == hash2
    assert len(hash1) == 64
