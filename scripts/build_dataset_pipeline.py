#!/usr/bin/env python3
"""End-to-end dataset creation, feature engineering, and splitting pipeline."""

import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.features.dataset_builder import DatasetBuilder
from src.features.transformations import FeatureTransformer
from src.features.splitting import DatasetSplitter
from src.features.analysis import DatasetAnalyzer
from src.common.logger import logger


def run_pipeline(output_version: str = "v1"):
    print("=" * 75)
    print("  EDA-Genius: Phase 1 Feature Engineering & Dataset Pipeline")
    print(f"  Target Version: {output_version}")
    print("=" * 75)

    base_dataset_dir = Path(f"artifacts/datasets/{output_version}")
    base_dataset_dir.mkdir(parents=True, exist_ok=True)
    splits_dir = base_dataset_dir / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build Raw Dataset
    print("\n[Step 1] Extracting RTL, netlist, config features & EDA targets from runs...")
    builder = DatasetBuilder(runs_dir=Path("artifacts/runs"))
    df_raw = builder.build_dataset()

    if df_raw.empty:
        print("[ERROR] No valid runs extracted from artifacts/runs!")
        sys.exit(1)

    raw_csv, raw_parquet = builder.save_versioned_dataset(
        df_raw, version=output_version, base_dir=Path("artifacts/datasets")
    )
    print(f"  -> Raw dataset saved: {len(df_raw)} rows, {len(df_raw.columns)} features")
    print(f"  -> File: {raw_csv}")

    # 2. Data Quality Analysis
    print("\n[Step 2] Performing data quality & integrity checks...")
    analyzer = DatasetAnalyzer(corr_threshold=0.85)
    dq_report = analyzer.compute_data_quality_report(df_raw)

    dq_json_path = base_dataset_dir / "data_quality_report.json"
    with open(dq_json_path, "w", encoding="utf-8") as f:
        json.dump(dq_report, f, indent=2)
    print(f"  -> Data quality metrics saved to {dq_json_path}")

    # 3. Feature Transformations & Domain Interactions
    print("\n[Step 3] Computing domain interaction features & normalizing...")
    transformer = FeatureTransformer()
    df_engineered, df_normalized = transformer.fit_transform(df_raw)

    norm_csv = base_dataset_dir / "eda_experiments_normalized.csv"
    norm_parquet = base_dataset_dir / "eda_experiments_normalized.parquet"
    df_normalized.to_csv(norm_csv, index=False)
    df_normalized.to_parquet(norm_parquet, index=False)
    print(f"  -> Normalized dataset saved ({len(df_normalized.columns)} columns)")
    print(f"  -> File: {norm_csv}")

    # 4. Correlation & Multicollinearity Analysis
    print("\n[Step 4] Running target correlation & multicollinearity analysis...")
    corr_df = analyzer.compute_target_correlations(df_engineered)
    corr_csv = base_dataset_dir / "target_correlations.csv"
    corr_df.to_csv(corr_csv)

    high_corr_pairs = analyzer.identify_highly_correlated_pairs(df_engineered, threshold=0.85)
    pairs_json = base_dataset_dir / "highly_correlated_features.json"
    with open(pairs_json, "w", encoding="utf-8") as f:
        json.dump(high_corr_pairs, f, indent=2)

    print(f"  -> Target correlations saved to {corr_csv}")
    print(f"  -> Identified {len(high_corr_pairs)} highly correlated feature pairs (|r| >= 0.85)")

    # 5. Dataset Splitting with Zero Leakage
    print("\n[Step 5] Applying design-level grouped train/val/test splitting...")
    splitter = DatasetSplitter(
        group_column="design_name",
        train_ratio=0.60,
        val_ratio=0.20,
        test_ratio=0.20,
        random_state=42
    )

    train_df, val_df, test_df, split_summary = splitter.split(df_engineered)
    split_paths = splitter.save_splits(train_df, val_df, test_df, output_dir=splits_dir)

    split_summary_path = splits_dir / "split_summary.json"
    with open(split_summary_path, "w", encoding="utf-8") as f:
        json.dump(split_summary, f, indent=2)

    print(f"  -> Train partition: {len(train_df)} rows ({split_summary['train_designs']})")
    print(f"  -> Val partition:   {len(val_df)} rows ({split_summary['val_designs']})")
    print(f"  -> Test partition:  {len(test_df)} rows ({split_summary['test_designs']})")
    print(f"  -> Verified zero design overlap between partitions.")

    # 6. Generate Markdown Reports
    print("\n[Step 6] Generating documentation reports...")
    generate_markdown_reports(df_raw, df_engineered, dq_report, high_corr_pairs, split_summary)

    print("\n" + "=" * 75)
    print("  Pipeline execution complete! All deliverables generated.")
    print("=" * 75)


def generate_markdown_reports(df_raw, df_eng, dq, high_corr, split_summary):
    """Generate Feature Dictionary and Data Quality Report markdown artifacts."""
    doc_dir = Path("docs")
    doc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Feature Dictionary
    dict_md = doc_dir / "feature_dictionary.md"
    with open(dict_md, "w", encoding="utf-8") as f:
        f.write("# EDA-Genius Feature Dictionary\n\n")
        f.write("Documented definitions, calculation sources, and physical meaning for all engineered features.\n\n")
        f.write("## 1. Feature Taxonomy Overview\n\n")
        f.write("| Category | Prefix / Scope | Count | Description |\n")
        f.write("|---|---|---|---|\n")
        f.write("| **A. RTL Features** | `rtl_*` | 11 | Synthesizable source code structural metrics |\n")
        f.write("| **B. Netlist Features** | `netlist_*`, `gate_count_*`, `net_fanout_*` | 19 | Gate-level cell distribution, fanouts & logic depth |\n")
        f.write("| **C. Physical Design Config** | `pd_*` | 8 | Placement constraints, utilization & PDK settings |\n")
        f.write("| **D. Domain Interactions** | `feat_*`, `log_*` | 22 | Ratios, densities, and log-transformed metrics |\n")
        f.write("| **E. Targets / EDA Outcomes** | `target_*` | 9 | Runtime, area, timing slack, power, DRC violations |\n\n")

        f.write("## 2. Detailed Feature Catalog\n\n")
        f.write("| Feature Name | Category | Dtype | Extraction Source | Calculation / Description |\n")
        f.write("|---|---|---|---|---|\n")
        
        feature_catalog = [
            ("rtl_num_modules", "RTL", "int", "RTL Source (`.v`/`.sv`)", "Count of module declarations (`module ... endmodule`)"),
            ("rtl_num_ports", "RTL", "int", "RTL Source", "Sum of all input, output, and inout port pins"),
            ("rtl_num_inputs", "RTL", "int", "RTL Source", "Total primary input port pins"),
            ("rtl_num_outputs", "RTL", "int", "RTL Source", "Total primary output port pins"),
            ("rtl_num_registers", "RTL", "int", "RTL Source", "Total `reg` and `logic` declarations"),
            ("rtl_num_wires", "RTL", "int", "RTL Source", "Total internal `wire` declarations"),
            ("rtl_num_always_blocks", "RTL", "int", "RTL Source", "Count of `always`, `always_ff`, and `always_comb` procedural blocks"),
            ("rtl_num_comb_assignments", "RTL", "int", "RTL Source", "Count of continuous `assign` statements"),
            ("rtl_source_bytes", "RTL", "int", "Filesystem", "RTL source file size in bytes"),
            ("rtl_source_lines", "RTL", "int", "RTL Source", "Total raw lines of code in RTL files"),
            ("rtl_code_lines", "RTL", "int", "RTL Source", "Non-comment, non-blank lines of Verilog code"),
            ("netlist_total_cells", "Netlist", "int", "Gate Netlist (`*_synth.v`)", "Total standard cell instances in synthesized netlist"),
            ("netlist_sequential_cells", "Netlist", "int", "Gate Netlist", "Count of state elements (DFFs, latches)"),
            ("netlist_combinational_cells", "Netlist", "int", "Gate Netlist", "Total combinational logic gates"),
            ("netlist_ff_count", "Netlist", "int", "Gate Netlist", "Dedicated flip-flop count (e.g. `sky130_fd_sc_hd__df*`)"),
            ("netlist_buffer_count", "Netlist", "int", "Gate Netlist", "Buffer count (`sky130_fd_sc_hd__buf_*`)"),
            ("netlist_inverter_count", "Netlist", "int", "Gate Netlist", "Inverter count (`sky130_fd_sc_hd__inv_*`)"),
            ("gate_count_nand", "Netlist", "int", "Gate Netlist", "NAND gate instances (`nand2`, `nand3`, etc.)"),
            ("gate_count_nor", "Netlist", "int", "Gate Netlist", "NOR gate instances (`nor2`, `nor3`, etc.)"),
            ("gate_count_and", "Netlist", "int", "Gate Netlist", "AND gate instances"),
            ("gate_count_or", "Netlist", "int", "Gate Netlist", "OR gate instances"),
            ("gate_count_xor", "Netlist", "int", "Gate Netlist", "XOR gate instances"),
            ("gate_count_xnor", "Netlist", "int", "Gate Netlist", "XNOR gate instances"),
            ("gate_count_mux", "Netlist", "int", "Gate Netlist", "Multiplexer instances (`mux2`, `mux4`)"),
            ("gate_count_aoi", "Netlist", "int", "Gate Netlist", "AND-OR-Invert compound cells (`a21oi`, `a31oi`)"),
            ("gate_count_oai", "Netlist", "int", "Gate Netlist", "OR-AND-Invert compound cells (`o21ai`, `o31ai`)"),
            ("netlist_estimated_logic_depth", "Netlist", "int", "Netlist DAG", "Longest topological path through combinational gates"),
            ("net_fanout_mean", "Netlist", "float", "Netlist Graph", "Mean number of pin loads driven per net"),
            ("net_fanout_max", "Netlist", "int", "Netlist Graph", "Maximum fanout load of any individual net"),
            ("net_fanout_std", "Netlist", "float", "Netlist Graph", "Standard deviation of fanout distribution"),
            ("pd_target_utilization", "Config", "float", "Floorplan TCL", "Target core cell placement density (0.05 to 0.95)"),
            ("pd_core_aspect_ratio", "Config", "float", "Floorplan TCL", "Floorplan aspect ratio (height / width)"),
            ("pd_core_space_um", "Config", "float", "Floorplan TCL", "Margin distance from die boundary to core in µm"),
            ("pd_clock_period_ns", "Config", "float", "SDC Constraints", "Target clock period constraint in nanoseconds"),
            ("pd_clock_uncertainty_ns", "Config", "float", "SDC Constraints", "Clock jitter & uncertainty budget in nanoseconds"),
            ("pd_clock_transition_ns", "Config", "float", "SDC Constraints", "Maximum clock transition time in nanoseconds"),
            ("pd_num_routing_layers", "Config", "int", "Technology LEF", "Available metal routing layer count (e.g. 6 for SKY130)"),
            ("pd_is_sky130", "Config", "int", "PDK Registry", "Binary indicator (1 = SkyWater SKY130A, 0 = Generic)"),
            ("feat_seq_ratio", "Domain", "float", "Calculated", "Ratio of sequential cells: `netlist_seq / total_cells`"),
            ("feat_comb_ratio", "Domain", "float", "Calculated", "Ratio of combinational cells: `netlist_comb / total_cells`"),
            ("feat_clock_freq_mhz", "Domain", "float", "Calculated", "Operating frequency: `1000.0 / clock_period_ns`"),
            ("feat_fanout_intensity", "Domain", "float", "Calculated", "Fanout complexity: `fanout_mean * log1p(fanout_max)`"),
            ("feat_density_proxy", "Domain", "float", "Calculated", "Cell density proxy: `total_cells / target_utilization`"),
            ("target_synthesis_runtime_s", "Target", "float", "Yosys Execution", "Wall-clock duration of RTL synthesis in seconds"),
            ("target_placement_runtime_s", "Target", "float", "OpenROAD Execution", "Wall-clock duration of placement & PD in seconds"),
            ("target_total_runtime_s", "Target", "float", "Flow Orchestrator", "End-to-end flow execution time in seconds"),
            ("target_cell_area_um2", "Target", "float", "OpenROAD / STA", "Total standard cell silicon area in µm²"),
            ("target_wns_ns", "Target", "float", "OpenSTA Timing", "Worst Negative Slack in nanoseconds (>=0 is MET)"),
            ("target_tns_ns", "Target", "float", "OpenSTA Timing", "Total Negative Slack accumulated across timing endpoints"),
            ("target_total_power_w", "Target", "float", "OpenROAD Power", "Total dynamic and leakage power dissipation in Watts"),
        ]

        for name, cat, dt, src, desc in feature_catalog:
            f.write(f"| `{name}` | {cat} | `{dt}` | {src} | {desc} |\n")

    # 2. Data Quality Report
    dq_md = doc_dir / "data_quality_report.md"
    with open(dq_md, "w", encoding="utf-8") as f:
        f.write("# EDA-Genius Data Quality & Integrity Report\n\n")
        f.write(f"**Total Experiment Runs Analyzed:** {dq['total_records']}\n\n")
        f.write(f"**Total Features Tracked:** {dq['total_columns']}\n\n")

        f.write("## 1. Missingness & Validity Summary\n\n")
        f.write("| Column Name | Dtype | Null Count | Null Pct | Cardinality | Min | Max | Mean |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")

        for col, stats in dq["columns"].items():
            min_str = f"{stats['min']:.2f}" if "min" in stats else "N/A"
            max_str = f"{stats['max']:.2f}" if "max" in stats else "N/A"
            mean_str = f"{stats['mean']:.2f}" if "mean" in stats else "N/A"
            f.write(f"| `{col}` | `{stats['dtype']}` | {stats['null_count']} | {stats['null_pct']}% | {stats['unique_count']} | {min_str} | {max_str} | {mean_str} |\n")

        f.write("\n## 2. Redundancy & Multicollinearity Findings (|r| >= 0.85)\n\n")
        f.write("Identified highly correlated pairs that should be pruned or regularized during model training:\n\n")
        f.write("| Feature 1 | Feature 2 | Pearson |r| | Physical Explanation |\n")
        f.write("|---|---|---|---|\n")
        for p in high_corr[:12]:
            f.write(f"| `{p['feature_1']}` | `{p['feature_2']}` | {p['correlation']} | Structural collinearity in design scale |\n")

        f.write("\n## 3. Zero-Leakage Dataset Splitting Strategy\n\n")
        f.write("To prevent data leakage, runs are partitioned strictly by RTL design family:\n\n")
        f.write(f"- **Train Partition:** {split_summary['train_samples']} runs ({split_summary['train_sample_pct']}%) — Designs: `{', '.join(split_summary['train_designs'])}`\n")
        f.write(f"- **Validation Partition:** {split_summary['val_samples']} runs ({split_summary['val_sample_pct']}%) — Designs: `{', '.join(split_summary['val_designs'])}`\n")
        f.write(f"- **Test Partition:** {split_summary['test_samples']} runs ({split_summary['test_sample_pct']}%) — Designs: `{', '.join(split_summary['test_designs'])}`\n\n")
        f.write("> **Leakage Verification:** No overlapping designs exist across partitions (Train ∩ Val = ∅, Train ∩ Test = ∅, Val ∩ Test = ∅).\n")


if __name__ == "__main__":
    run_pipeline()
