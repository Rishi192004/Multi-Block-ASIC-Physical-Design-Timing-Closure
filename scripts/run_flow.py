#!/usr/bin/env python3
"""CLI driver for EDA-Genius flow execution and batch regressions."""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.types import DesignInput
from src.common.config import load_config
from src.orchestration.flow_orchestrator import FlowOrchestrator
from src.database.record_adapter import RecordAdapter
from src.common.logger import logger


BENCHMARK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "alu": {
        "top_module": "alu",
        "file": "benchmarks/alu/alu.v",
        "clock_period_ns": 5.0,
        "clock_port": "clk"
    },
    "fsm_traffic": {
        "top_module": "fsm_traffic",
        "file": "benchmarks/fsm_traffic/fsm_traffic.v",
        "clock_period_ns": 10.0,
        "clock_port": "clk"
    },
    "uart_tx": {
        "top_module": "uart_tx",
        "file": "benchmarks/uart_tx/uart_tx.v",
        "clock_period_ns": 8.0,
        "clock_port": "clk"
    },
    "fifo_sync": {
        "top_module": "fifo_sync",
        "file": "benchmarks/fifo_sync/fifo_sync.v",
        "clock_period_ns": 6.0,
        "clock_port": "clk"
    },
    "booth_multiplier": {
        "top_module": "booth_multiplier",
        "file": "benchmarks/booth_multiplier/booth_multiplier.v",
        "clock_period_ns": 12.0,
        "clock_port": "clk"
    }
}


def run_single_design(
    orchestrator: FlowOrchestrator,
    design_name: str,
    target_pdk: str = "generic",
    run_pd: bool = False,
    recover_id: str = None
) -> Dict[str, Any]:
    """Run flow on a single benchmark design."""
    if design_name not in BENCHMARK_REGISTRY:
        raise ValueError(f"Unknown benchmark design '{design_name}'. Registered: {list(BENCHMARK_REGISTRY.keys())}")

    info = BENCHMARK_REGISTRY[design_name]
    v_path = Path(info["file"])

    design_in = DesignInput(
        design_name=design_name,
        top_module=info["top_module"],
        verilog_files=[v_path],
        clock_period_ns=info["clock_period_ns"],
        clock_port_name=info["clock_port"],
        target_pdk=target_pdk
    )

    pdk_config = None
    if run_pd:
        cfg = load_config()
        if target_pdk in cfg.pdks:
            pdk_config = cfg.pdks[target_pdk].model_dump()

    record = orchestrator.execute_flow(
        design_input=design_in,
        pdk_config=pdk_config,
        run_physical_design=run_pd,
        recover_run_id=recover_id
    )

    pg_payload = RecordAdapter.to_postgres_payload(record)
    return {
        "record": record,
        "pg_payload": pg_payload
    }


def main():
    parser = argparse.ArgumentParser(description="EDA-Genius Automated Flow Runner")
    parser.add_argument("--design", type=str, help="Specific benchmark design to run (alu, uart_tx, etc.)")
    parser.add_argument("--all-benchmarks", action="store_true", help="Execute regression across all 5 benchmarks")
    parser.add_argument("--pdk", type=str, default="generic", help="Target PDK (generic, sky130hd)")
    parser.add_argument("--run-pd", action="store_true", help="Run OpenROAD physical design flow after synthesis")
    parser.add_argument("--recover", type=str, help="Run ID for partial run recovery")
    parser.add_argument("--export-postgres-json", type=str, default="./artifacts/reports/postgres_payloads.json",
                        help="Path to save PostgreSQL relational payloads")

    args = parser.parse_args()
    orchestrator = FlowOrchestrator()

    designs_to_run = []
    if args.all_benchmarks:
        designs_to_run = list(BENCHMARK_REGISTRY.keys())
    elif args.design:
        designs_to_run = [args.design]
    else:
        parser.print_help()
        sys.exit(1)

    print("=" * 70)
    print("  EDA-Genius: Automated EDA Orchestration & PPA Extraction")
    print(f"  Target PDK: {args.pdk} | Physical Design Enabled: {args.run_pd}")
    print(f"  Designs to Execute: {', '.join(designs_to_run)}")
    print("=" * 70)

    results = []
    pg_payloads = []

    for d_name in designs_to_run:
        print(f"\n>>> Running Design: {d_name} ...")
        res = run_single_design(
            orchestrator=orchestrator,
            design_name=d_name,
            target_pdk=args.pdk,
            run_pd=args.run_pd,
            recover_id=args.recover
        )
        rec = res["record"]
        pg_payloads.append(res["pg_payload"])
        results.append(rec)

        print(f"    Status: {rec.status.value}")
        print(f"    Synthesis Runtime: {rec.synthesis_runtime_s}s")
        print(f"    Total Cells: {rec.metrics.get('total_cells', 0)}")
        print(f"    Cell Types: {rec.cell_statistics}")
        print(f"    Artifact: {rec.artifacts.get('netlist_v')}")

    # Export postgres payloads
    out_pg = Path(args.export_postgres_json)
    out_pg.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pg, "w", encoding="utf-8") as f:
        json.dump(pg_payloads, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Execution complete for {len(results)} designs.")
    print(f"Master CSV Report: artifacts/reports/master_experiments.csv")
    print(f"PostgreSQL Ingestion Payload: {out_pg}")
    print("=" * 70)


if __name__ == "__main__":
    main()
