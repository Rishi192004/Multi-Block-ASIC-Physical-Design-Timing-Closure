"""Unit tests for relational PostgreSQL record adapter."""

from datetime import datetime
from src.common.types import ExperimentRecord, RunStatus
from src.database.record_adapter import RecordAdapter


def test_record_adapter_transformation():
    record = ExperimentRecord(
        run_id="run_alu_test_01",
        design_name="alu",
        top_module="alu",
        status=RunStatus.COMPLETED,
        rtl_hash="a1b2c3d4e5f67890",
        config_hash="f0e1d2c3b4a59687",
        tool_versions={"yosys": "0.9"},
        target_pdk="generic",
        clock_period_ns=10.0,
        started_at=datetime(2026, 11, 17, 12, 0, 0),
        completed_at=datetime(2026, 11, 17, 12, 0, 15),
        total_runtime_s=15.0,
        synthesis_runtime_s=14.2,
        metrics={
            "total_cells": 184,
            "chip_area_um2": 1450.25,
            "wns": 2.45
        },
        cell_statistics={"$_AND_": 42, "$_OR_": 38},
        artifacts={"netlist_v": "/path/to/netlist.v"},
        raw_reports={"yosys_log": "/path/to/yosys.log"}
    )

    pg_payload = RecordAdapter.to_postgres_payload(record)

    assert "design" in pg_payload
    assert pg_payload["design"]["name"] == "alu"

    assert "run" in pg_payload
    assert pg_payload["run"]["status"] == "COMPLETED"
    assert pg_payload["run"]["total_wall_time_s"] == 15.0

    assert "stages" in pg_payload
    assert len(pg_payload["stages"]) == 1
    assert pg_payload["stages"][0]["stage_name"] == "SYNTHESIS"
    assert pg_payload["stages"][0]["runtime_s"] == 14.2

    assert "metrics" in pg_payload
    assert len(pg_payload["metrics"]) == 3
    metric_names = [m["metric_name"] for m in pg_payload["metrics"]]
    assert "total_cells" in metric_names
    assert "wns" in metric_names
