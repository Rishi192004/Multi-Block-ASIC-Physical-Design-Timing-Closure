"""Unit tests for RTL, Netlist, Config extractors, transformations, and grouped dataset splitting."""

import pytest
from pathlib import Path
import pandas as pd
import numpy as np

from src.features.rtl_extractor import RTLExtractor, RTLFeatures
from src.features.netlist_extractor import NetlistExtractor, NetlistFeatures
from src.features.config_extractor import ConfigExtractor, PDConfigFeatures
from src.features.transformations import FeatureTransformer
from src.features.splitting import DatasetSplitter
from src.features.analysis import DatasetAnalyzer


SAMPLE_VERILOG = """
module counter_8bit (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    output reg  [7:0] count,
    output wire       overflow
);

    parameter MAX_VAL = 8'd255;

    wire [7:0] next_count;
    assign next_count = count + 1'b1;
    assign overflow = (count == MAX_VAL);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'd0;
        else if (enable)
            count <= next_count;
    end

endmodule
"""

SAMPLE_NETLIST = """
module counter_8bit (clk, rst_n, enable, count, overflow);
  input clk, rst_n, enable;
  output [7:0] count;
  output overflow;

  wire _00_, _01_, _02_, _03_;

  sky130_fd_sc_hd__nand2_1 _g1_ ( .A(clk), .B(enable), .Y(_00_) );
  sky130_fd_sc_hd__nor2_1  _g2_ ( .A(_00_), .B(rst_n), .Y(_01_) );
  sky130_fd_sc_hd__dfxtp_1 _ff0_ ( .CLK(clk), .D(_01_), .Q(_02_) );
  sky130_fd_sc_hd__dfxtp_1 _ff1_ ( .CLK(clk), .D(_02_), .Q(_03_) );
  sky130_fd_sc_hd__inv_1   _inv_ ( .A(_03_), .Y(overflow) );
endmodule
"""


# -------------------------------------------------------------------------
# 1. RTL Extractor Tests
# -------------------------------------------------------------------------
def test_rtl_extractor_from_text():
    extractor = RTLExtractor()
    feats = extractor.extract_from_text(SAMPLE_VERILOG)

    assert feats.rtl_num_modules == 1
    assert feats.rtl_num_ports == 5  # clk, rst_n, enable, count, overflow
    assert feats.rtl_num_inputs == 3
    assert feats.rtl_num_outputs == 2
    assert feats.rtl_num_registers == 1  # count
    assert feats.rtl_num_wires >= 1      # next_count
    assert feats.rtl_num_always_blocks == 1
    assert feats.rtl_num_comb_assignments == 2
    assert feats.rtl_has_parameters is True
    assert feats.rtl_source_lines > 10
    assert feats.rtl_code_lines > 0


def test_rtl_extractor_real_benchmark_alu():
    extractor = RTLExtractor()
    alu_path = Path("benchmarks/alu/alu.v")
    assert alu_path.exists()
    feats = extractor.extract_from_file(alu_path)

    assert feats.rtl_num_modules >= 1
    assert feats.rtl_num_ports >= 4  # a, b, alu_op, result, overflow, etc.
    assert feats.rtl_source_bytes > 100


# -------------------------------------------------------------------------
# 2. Netlist Extractor Tests
# -------------------------------------------------------------------------
def test_netlist_extractor_from_text():
    extractor = NetlistExtractor()
    feats = extractor.extract_from_text(SAMPLE_NETLIST)

    assert feats.netlist_total_cells == 5
    assert feats.netlist_sequential_cells == 2  # two dfxtp_1
    assert feats.netlist_ff_count == 2
    assert feats.netlist_combinational_cells == 3  # nand2, nor2, inv
    assert feats.gate_count_nand == 1
    assert feats.gate_count_nor == 1
    assert feats.netlist_inverter_count == 1
    assert feats.net_fanout_max >= 1
    assert feats.netlist_estimated_logic_depth >= 1


def test_netlist_extractor_empty():
    extractor = NetlistExtractor()
    feats = extractor.extract_from_text("")
    assert feats.netlist_total_cells == 0
    assert feats.netlist_estimated_logic_depth == 0


# -------------------------------------------------------------------------
# 3. Config Extractor Tests
# -------------------------------------------------------------------------
def test_config_extractor_defaults():
    extractor = ConfigExtractor()
    record = {
        "target_pdk": "sky130hd",
        "clock_period_ns": 8.0,
    }
    feats = extractor.extract_from_run(record)

    assert feats.pd_target_pdk == "sky130hd"
    assert feats.pd_is_sky130 is True
    assert feats.pd_clock_period_ns == 8.0
    assert feats.pd_num_routing_layers == 6


# -------------------------------------------------------------------------
# 4. Feature Transformations Tests
# -------------------------------------------------------------------------
def test_feature_transformer_scaling():
    transformer = FeatureTransformer()

    # Synthetic sample dataframe
    data = pd.DataFrame({
        "design_name": ["alu", "uart_tx", "fifo"],
        "netlist_total_cells": [1000, 200, 800],
        "netlist_sequential_cells": [50, 40, 200],
        "netlist_combinational_cells": [950, 160, 600],
        "netlist_ff_count": [50, 40, 200],
        "net_fanout_mean": [2.5, 1.8, 2.2],
        "net_fanout_max": [30, 12, 25],
        "netlist_estimated_logic_depth": [15, 6, 12],
        "pd_target_utilization": [0.4, 0.5, 0.6],
        "pd_clock_period_ns": [5.0, 10.0, 8.0],
        "rtl_source_lines": [120, 80, 150],
        "rtl_source_bytes": [4000, 2500, 5000],
        "rtl_code_lines": [90, 60, 110],
        "gate_count_nand": [100, 20, 80],
        "gate_count_nor": [50, 10, 40],
        "gate_count_and": [80, 15, 60],
        "gate_count_or": [90, 25, 70],
        "gate_count_mux": [150, 10, 90],
        "gate_count_aoi": [40, 5, 30],
        "gate_count_oai": [30, 5, 20],
        "total_nets": [1100, 220, 850],
        "target_cell_area_um2": [5000.0, 1200.0, 4200.0],
        "target_synthesis_runtime_s": [3.2, 0.8, 2.1],
        "target_placement_runtime_s": [1.5, 0.6, 1.2],
        "target_total_runtime_s": [4.7, 1.4, 3.3],
        "target_wns_ns": [-1.2, 0.1, -0.5]
    })

    df_eng, df_scaled = transformer.fit_transform(data)

    # Assert new engineered columns exist
    assert "feat_seq_ratio" in df_eng.columns
    assert "feat_comb_ratio" in df_eng.columns
    assert "feat_clock_freq_mhz" in df_eng.columns
    assert "log_netlist_total_cells" in df_eng.columns

    # Scaled numeric features should have zero mean
    scaled_feature = df_scaled["feat_clock_freq_mhz"]
    assert abs(scaled_feature.mean()) < 1e-6
    assert abs(scaled_feature.std(ddof=0) - 1.0) < 1e-4


# -------------------------------------------------------------------------
# 5. Dataset Grouped Splitting & Zero-Leakage Tests
# -------------------------------------------------------------------------
def test_dataset_grouped_splitter_zero_leakage():
    # 6 distinct design families, multiple runs per family
    designs = ["alu", "uart_tx", "fifo_sync", "fsm_traffic", "booth_multiplier", "priority_encoder"]
    rows = []
    for d in designs:
        for i in range(5):  # 5 runs per design
            rows.append({
                "run_id": f"run_{d}_{i}",
                "design_name": d,
                "netlist_total_cells": np.random.randint(100, 1000),
                "target_total_runtime_s": np.random.uniform(1.0, 10.0)
            })

    df = pd.DataFrame(rows)
    splitter = DatasetSplitter(group_column="design_name", train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
    train_df, val_df, test_df, summary = splitter.split(df)

    # 1. Total samples conserved
    assert len(train_df) + len(val_df) + len(test_df) == len(df)

    # 2. Strict Zero Leakage: No design family exists in multiple partitions
    train_designs = set(train_df["design_name"])
    val_designs = set(val_df["design_name"])
    test_designs = set(test_df["design_name"])

    assert len(train_designs.intersection(val_designs)) == 0
    assert len(train_designs.intersection(test_designs)) == 0
    assert len(val_designs.intersection(test_designs)) == 0

    # 3. All designs partitioned
    assert train_designs.union(val_designs).union(test_designs) == set(designs)


# -------------------------------------------------------------------------
# 6. Dataset Analyzer & Correlation Tests
# -------------------------------------------------------------------------
def test_dataset_analyzer():
    data = pd.DataFrame({
        "cell_count": [100, 200, 300, 400, 500],
        "wire_count": [105, 204, 302, 401, 503],  # almost perfectly collinear
        "independent_val": [5, 2, 8, 1, 9],
        "target_synthesis_runtime_s": [1.1, 2.0, 3.1, 4.0, 5.2]
    })

    analyzer = DatasetAnalyzer(corr_threshold=0.85)
    dq = analyzer.compute_data_quality_report(data)
    assert dq["total_records"] == 5
    assert dq["columns"]["cell_count"]["null_count"] == 0

    pairs = analyzer.identify_highly_correlated_pairs(data, threshold=0.90)
    assert len(pairs) >= 1
    assert pairs[0]["feature_1"] in ("cell_count", "wire_count")
    assert pairs[0]["correlation"] > 0.99
