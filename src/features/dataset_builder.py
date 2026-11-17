"""Dataset builder aggregating RTL, netlist, config features and EDA targets across runs."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from src.features.rtl_extractor import RTLExtractor, RTLFeatures
from src.features.netlist_extractor import NetlistExtractor, NetlistFeatures
from src.features.config_extractor import ConfigExtractor, PDConfigFeatures
from src.common.logger import logger


BENCHMARK_RTL_DIR = Path("benchmarks")


class DatasetBuilder:
    """Builds unified tabular ML datasets from raw EDA experiment runs."""

    def __init__(self, runs_dir: Path = Path("artifacts/runs")):
        self.runs_dir = runs_dir
        self.rtl_extractor = RTLExtractor()
        self.netlist_extractor = NetlistExtractor()
        self.config_extractor = ConfigExtractor()

    def _find_rtl_files(self, design_name: str) -> List[Path]:
        """Locate source RTL files for a benchmark design."""
        clean_name = design_name.replace("_pd_test", "").replace("integration_", "").replace("batch_", "")
        design_dir = BENCHMARK_RTL_DIR / clean_name
        if design_dir.exists():
            return list(design_dir.glob("*.v")) + list(design_dir.glob("*.sv"))
        # Fallback to searching all benchmarks
        matches = list(BENCHMARK_RTL_DIR.glob(f"**/{clean_name}.v"))
        return matches

    def extract_single_run(self, run_dir: Path) -> Optional[Dict[str, Any]]:
        """Extract all features and targets from an individual experiment run directory."""
        record_file = run_dir / "experiment_record.json"
        if not record_file.exists():
            return None

        try:
            record = json.loads(record_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read experiment record in {run_dir}: {e}")
            return None

        run_id = record.get("run_id", run_dir.name)
        design_name = record.get("design_name", "unknown")
        status = record.get("status", "UNKNOWN")
        target_pdk = record.get("target_pdk", "generic")

        # 1. RTL Features (Category A)
        rtl_files = self._find_rtl_files(design_name)
        if rtl_files:
            rtl_feats = self.rtl_extractor.extract_from_files(rtl_files)
        else:
            rtl_feats = RTLFeatures()

        # 2. Netlist Features (Category B)
        # Search for netlist artifact or in run dir
        netlist_path = None
        if "artifacts" in record and "netlist_v" in record["artifacts"]:
            p = Path(record["artifacts"]["netlist_v"])
            if p.exists():
                netlist_path = p

        if not netlist_path:
            synth_files = list(run_dir.glob("*_synth.v"))
            if synth_files:
                netlist_path = synth_files[0]

        if netlist_path and netlist_path.exists():
            netlist_feats = self.netlist_extractor.extract_from_file(netlist_path)
        else:
            # Fallback to cell statistics stored in experiment_record
            cell_stats = record.get("cell_statistics", {})
            total_cells = sum(cell_stats.values()) if cell_stats else int(record.get("metrics", {}).get("total_cells", 0))
            seq_cells = sum(v for k, v in cell_stats.items() if "dff" in k.lower() or "df" in k.lower())
            comb_cells = max(0, total_cells - seq_cells)
            netlist_feats = NetlistFeatures(
                netlist_total_cells=total_cells,
                netlist_sequential_cells=seq_cells,
                netlist_combinational_cells=comb_cells,
                netlist_ff_count=seq_cells
            )

        # 3. Configuration Features (Category C)
        cfg_feats = self.config_extractor.extract_from_run(record, workdir=run_dir)

        # 4. Target / EDA Outcomes (Category D)
        metrics = record.get("metrics", {})
        synth_runtime = float(record.get("synthesis_runtime_s", 0.0))
        pd_runtime = float(record.get("physical_design_runtime_s", 0.0))
        total_runtime = float(record.get("total_runtime_s", synth_runtime + pd_runtime))

        # Cell Area
        cell_area = metrics.get("chip_area_um2") or metrics.get("design_area_um2")
        if cell_area is None:
            # Estimate from cell count if unplaced
            cell_area = float(netlist_feats.netlist_total_cells * 4.5)  # generic proxy
        else:
            cell_area = float(cell_area)

        # Timing (WNS, TNS)
        wns_raw = metrics.get("wns")
        tns_raw = metrics.get("tns")
        is_missing_timing = (wns_raw is None or wns_raw == "")
        target_wns = float(wns_raw) if not is_missing_timing else 0.0
        target_tns = float(tns_raw) if not is_missing_timing else 0.0

        # Power
        pwr_raw = metrics.get("total_power_w")
        is_missing_power = (pwr_raw is None or pwr_raw == "")
        target_power = float(pwr_raw) if not is_missing_power else 0.0

        # Wirelength & DRC
        wl_raw = metrics.get("total_wirelength_um")
        is_missing_wirelength = (wl_raw is None or wl_raw == "")
        target_wirelength = float(wl_raw) if not is_missing_wirelength else 0.0
        target_drc = float(metrics.get("drc_violations", 0))

        # Flatten into row dictionary
        row = {
            # Metadata & Identifiers
            "run_id": run_id,
            "design_name": design_name.replace("_pd_test", "").replace("integration_", "").replace("batch_", ""),
            "original_design_name": design_name,
            "run_status": status,
            "is_success": (status == "COMPLETED"),
            "target_pdk": target_pdk,

            # Category A: RTL-level features
            "rtl_num_modules": rtl_feats.rtl_num_modules,
            "rtl_num_ports": rtl_feats.rtl_num_ports,
            "rtl_num_inputs": rtl_feats.rtl_num_inputs,
            "rtl_num_outputs": rtl_feats.rtl_num_outputs,
            "rtl_num_registers": rtl_feats.rtl_num_registers,
            "rtl_num_wires": rtl_feats.rtl_num_wires,
            "rtl_num_always_blocks": rtl_feats.rtl_num_always_blocks,
            "rtl_num_comb_assignments": rtl_feats.rtl_num_comb_assignments,
            "rtl_source_bytes": rtl_feats.rtl_source_bytes,
            "rtl_source_lines": rtl_feats.rtl_source_lines,
            "rtl_code_lines": rtl_feats.rtl_code_lines,

            # Category B: Netlist-level features
            "netlist_total_cells": netlist_feats.netlist_total_cells,
            "netlist_sequential_cells": netlist_feats.netlist_sequential_cells,
            "netlist_combinational_cells": netlist_feats.netlist_combinational_cells,
            "netlist_ff_count": netlist_feats.netlist_ff_count,
            "netlist_latch_count": netlist_feats.netlist_latch_count,
            "netlist_buffer_count": netlist_feats.netlist_buffer_count,
            "netlist_inverter_count": netlist_feats.netlist_inverter_count,
            "gate_count_nand": netlist_feats.gate_count_nand,
            "gate_count_nor": netlist_feats.gate_count_nor,
            "gate_count_and": netlist_feats.gate_count_and,
            "gate_count_or": netlist_feats.gate_count_or,
            "gate_count_xor": netlist_feats.gate_count_xor,
            "gate_count_xnor": netlist_feats.gate_count_xnor,
            "gate_count_mux": netlist_feats.gate_count_mux,
            "gate_count_aoi": netlist_feats.gate_count_aoi,
            "gate_count_oai": netlist_feats.gate_count_oai,
            "netlist_estimated_logic_depth": netlist_feats.netlist_estimated_logic_depth,
            "net_fanout_mean": netlist_feats.net_fanout_mean,
            "net_fanout_max": netlist_feats.net_fanout_max,
            "net_fanout_std": netlist_feats.net_fanout_std,
            "total_nets": netlist_feats.total_nets,

            # Category C: Configuration features
            "pd_target_utilization": cfg_feats.pd_target_utilization,
            "pd_core_aspect_ratio": cfg_feats.pd_core_aspect_ratio,
            "pd_core_space_um": cfg_feats.pd_core_space_um,
            "pd_clock_period_ns": cfg_feats.pd_clock_period_ns,
            "pd_clock_uncertainty_ns": cfg_feats.pd_clock_uncertainty_ns,
            "pd_clock_transition_ns": cfg_feats.pd_clock_transition_ns,
            "pd_num_routing_layers": cfg_feats.pd_num_routing_layers,
            "pd_is_sky130": int(cfg_feats.pd_is_sky130),

            # Category D: Target / Outcome variables
            "target_synthesis_runtime_s": synth_runtime,
            "target_placement_runtime_s": pd_runtime,
            "target_total_runtime_s": total_runtime,
            "target_cell_area_um2": cell_area,
            "target_wns_ns": target_wns,
            "target_tns_ns": target_tns,
            "target_total_power_w": target_power,
            "target_total_wirelength_um": target_wirelength,
            "target_routing_violations": target_drc,

            # Data Quality & Missingness Indicators
            "is_missing_timing": int(is_missing_timing),
            "is_missing_power": int(is_missing_power),
            "is_missing_wirelength": int(is_missing_wirelength),
        }
        return row

    def build_dataset(self) -> pd.DataFrame:
        """Scan all runs and construct unified DataFrame."""
        rows = []
        for run_dir in sorted(self.runs_dir.iterdir()):
            if run_dir.is_dir():
                row = self.extract_single_run(run_dir)
                if row:
                    rows.append(row)

        df = pd.DataFrame(rows)
        logger.info(f"Built raw experiment dataset with {len(df)} rows and {len(df.columns)} columns")
        return df

    def save_versioned_dataset(
        self,
        df: pd.DataFrame,
        version: str = "v1",
        base_dir: Path = Path("artifacts/datasets")
    ) -> Tuple[Path, Path]:
        """Save dataset to versioned directory in both CSV and Parquet formats."""
        out_dir = base_dir / version
        out_dir.mkdir(parents=True, exist_ok=True)

        csv_path = out_dir / "eda_experiments_raw.csv"
        parquet_path = out_dir / "eda_experiments_raw.parquet"

        df.to_csv(csv_path, index=False)
        df.to_parquet(parquet_path, index=False)
        logger.info(f"Saved versioned dataset to {csv_path} and {parquet_path}")

        return csv_path, parquet_path
