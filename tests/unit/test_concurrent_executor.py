"""Unit tests for concurrent batch execution via FlowOrchestrator.execute_batch()."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.common.types import DesignInput, ExperimentRecord, RunStatus, StageName
from src.orchestration.flow_orchestrator import FlowOrchestrator


def _make_mock_record(design_name: str) -> ExperimentRecord:
    return ExperimentRecord(
        run_id=f"run_{design_name}_mock",
        design_name=design_name,
        top_module=design_name,
        status=RunStatus.COMPLETED,
        rtl_hash="a" * 64,
        config_hash="b" * 64,
        tool_versions={"yosys": "0.9"},
        target_pdk="generic",
        clock_period_ns=10.0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        synthesis_runtime_s=1.5,
        total_runtime_s=1.5,
        metrics={"total_cells": 100}
    )


def test_execute_batch_calls_execute_flow_for_each_design(tmp_path):
    """execute_batch must call execute_flow once per design in the batch."""
    orch = FlowOrchestrator(
        runs_dir=tmp_path / "runs",
        reports_dir=tmp_path / "reports"
    )

    designs_names = ["alu", "uart_tx", "fifo_sync"]
    mock_records = {n: _make_mock_record(n) for n in designs_names}

    # We patch execute_flow to return a mock record and avoid real tool calls
    call_tracker = []

    def mock_execute_flow(design_input, **kwargs):
        call_tracker.append(design_input.design_name)
        return mock_records[design_input.design_name]

    with patch.object(orch, "execute_flow", side_effect=mock_execute_flow):
        alu_file = Path("benchmarks/alu/alu.v")
        uart_file = Path("benchmarks/uart_tx/uart_tx.v")
        fifo_file = Path("benchmarks/fifo_sync/fifo_sync.v")

        designs = [
            (DesignInput(design_name="alu", top_module="alu",
                         verilog_files=[alu_file]), None),
            (DesignInput(design_name="uart_tx", top_module="uart_tx",
                         verilog_files=[uart_file]), None),
            (DesignInput(design_name="fifo_sync", top_module="fifo_sync",
                         verilog_files=[fifo_file]), None),
        ]

        results = orch.execute_batch(designs, max_workers=2)

    # All 3 designs must have been processed
    assert len(results) == 3
    assert set(call_tracker) == {"alu", "uart_tx", "fifo_sync"}


def test_execute_batch_with_max_workers_1_is_sequential(tmp_path):
    """execute_batch with max_workers=1 must still return all results correctly."""
    orch = FlowOrchestrator(
        runs_dir=tmp_path / "runs",
        reports_dir=tmp_path / "reports"
    )
    mock_record = _make_mock_record("alu")

    with patch.object(orch, "execute_flow", return_value=mock_record):
        alu_file = Path("benchmarks/alu/alu.v")
        designs = [
            (DesignInput(design_name="alu", top_module="alu",
                         verilog_files=[alu_file]), None)
        ]
        results = orch.execute_batch(designs, max_workers=1)

    assert len(results) == 1
    assert results[0].design_name == "alu"


def test_execute_batch_handles_partial_failure(tmp_path):
    """execute_batch must return successful records even when one design fails."""
    orch = FlowOrchestrator(
        runs_dir=tmp_path / "runs",
        reports_dir=tmp_path / "reports"
    )

    def mock_execute_flow(design_input, **kwargs):
        if design_input.design_name == "alu":
            raise RuntimeError("Simulated tool failure")
        return _make_mock_record(design_input.design_name)

    with patch.object(orch, "execute_flow", side_effect=mock_execute_flow):
        alu_file = Path("benchmarks/alu/alu.v")
        uart_file = Path("benchmarks/uart_tx/uart_tx.v")
        designs = [
            (DesignInput(design_name="alu", top_module="alu",
                         verilog_files=[alu_file]), None),
            (DesignInput(design_name="uart_tx", top_module="uart_tx",
                         verilog_files=[uart_file]), None),
        ]
        # Must not raise; partial failure is absorbed and None filtered out
        results = orch.execute_batch(designs, max_workers=2)

    # Only the successful design is returned
    assert len(results) == 1
    assert results[0].design_name == "uart_tx"
