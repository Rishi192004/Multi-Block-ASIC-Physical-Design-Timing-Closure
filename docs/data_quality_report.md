# EDA-Genius Data Quality & Integrity Report

**Total Experiment Runs Analyzed:** 42

**Total Features Tracked:** 58

## 1. Missingness & Validity Summary

| Column Name | Dtype | Null Count | Null Pct | Cardinality | Min | Max | Mean |
|---|---|---|---|---|---|---|---|
| `run_id` | `str` | 0 | 0.0% | 42 | N/A | N/A | N/A |
| `design_name` | `str` | 0 | 0.0% | 6 | N/A | N/A | N/A |
| `original_design_name` | `str` | 0 | 0.0% | 7 | N/A | N/A | N/A |
| `run_status` | `str` | 0 | 0.0% | 2 | N/A | N/A | N/A |
| `is_success` | `bool` | 0 | 0.0% | 2 | 0.00 | 1.00 | 0.69 |
| `target_pdk` | `str` | 0 | 0.0% | 2 | N/A | N/A | N/A |
| `rtl_num_modules` | `int64` | 0 | 0.0% | 1 | 1.00 | 1.00 | 1.00 |
| `rtl_num_ports` | `int64` | 0 | 0.0% | 4 | 5.00 | 11.00 | 7.62 |
| `rtl_num_inputs` | `int64` | 0 | 0.0% | 3 | 3.00 | 5.00 | 4.00 |
| `rtl_num_outputs` | `int64` | 0 | 0.0% | 4 | 2.00 | 6.00 | 3.62 |
| `rtl_num_registers` | `int64` | 0 | 0.0% | 6 | 1.00 | 9.00 | 5.83 |
| `rtl_num_wires` | `int64` | 0 | 0.0% | 6 | 3.00 | 9.00 | 5.79 |
| `rtl_num_always_blocks` | `int64` | 0 | 0.0% | 4 | 1.00 | 4.00 | 1.64 |
| `rtl_num_comb_assignments` | `int64` | 0 | 0.0% | 5 | 0.00 | 5.00 | 1.79 |
| `rtl_source_bytes` | `int64` | 0 | 0.0% | 6 | 2030.00 | 4055.00 | 2893.93 |
| `rtl_source_lines` | `int64` | 0 | 0.0% | 6 | 53.00 | 126.00 | 87.81 |
| `rtl_code_lines` | `int64` | 0 | 0.0% | 6 | 42.00 | 113.00 | 75.81 |
| `netlist_total_cells` | `int64` | 0 | 0.0% | 6 | 0.00 | 1107.00 | 203.76 |
| `netlist_sequential_cells` | `int64` | 0 | 0.0% | 5 | 0.00 | 285.00 | 29.33 |
| `netlist_combinational_cells` | `int64` | 0 | 0.0% | 6 | 0.00 | 1107.00 | 174.43 |
| `netlist_ff_count` | `int64` | 0 | 0.0% | 5 | 0.00 | 285.00 | 29.33 |
| `netlist_latch_count` | `int64` | 0 | 0.0% | 1 | 0.00 | 0.00 | 0.00 |
| `netlist_buffer_count` | `int64` | 0 | 0.0% | 5 | 0.00 | 33.00 | 4.00 |
| `netlist_inverter_count` | `int64` | 0 | 0.0% | 6 | 0.00 | 24.00 | 4.19 |
| `gate_count_nand` | `int64` | 0 | 0.0% | 6 | 0.00 | 202.00 | 33.71 |
| `gate_count_nor` | `int64` | 0 | 0.0% | 6 | 0.00 | 206.00 | 29.19 |
| `gate_count_and` | `int64` | 0 | 0.0% | 5 | 0.00 | 31.00 | 7.57 |
| `gate_count_or` | `int64` | 0 | 0.0% | 4 | 0.00 | 14.00 | 1.52 |
| `gate_count_xor` | `int64` | 0 | 0.0% | 4 | 0.00 | 25.00 | 3.24 |
| `gate_count_xnor` | `int64` | 0 | 0.0% | 1 | 0.00 | 0.00 | 0.00 |
| `gate_count_mux` | `int64` | 0 | 0.0% | 5 | 0.00 | 325.00 | 27.24 |
| `gate_count_aoi` | `int64` | 0 | 0.0% | 6 | 0.00 | 150.00 | 18.86 |
| `gate_count_oai` | `int64` | 0 | 0.0% | 5 | 0.00 | 161.00 | 21.33 |
| `netlist_estimated_logic_depth` | `int64` | 0 | 0.0% | 5 | 0.00 | 28.00 | 5.29 |
| `net_fanout_mean` | `float64` | 0 | 0.0% | 6 | 0.00 | 2.59 | 1.31 |
| `net_fanout_max` | `int64` | 0 | 0.0% | 6 | 0.00 | 285.00 | 38.19 |
| `net_fanout_std` | `float64` | 0 | 0.0% | 6 | 0.00 | 11.04 | 2.79 |
| `total_nets` | `int64` | 0 | 0.0% | 6 | 0.00 | 1169.00 | 215.95 |
| `pd_target_utilization` | `float64` | 0 | 0.0% | 2 | 0.40 | 0.50 | 0.45 |
| `pd_core_aspect_ratio` | `float64` | 0 | 0.0% | 1 | 1.00 | 1.00 | 1.00 |
| `pd_core_space_um` | `float64` | 0 | 0.0% | 1 | 10.00 | 10.00 | 10.00 |
| `pd_clock_period_ns` | `float64` | 0 | 0.0% | 6 | 5.00 | 12.00 | 8.33 |
| `pd_clock_uncertainty_ns` | `float64` | 0 | 0.0% | 1 | 0.25 | 0.25 | 0.25 |
| `pd_clock_transition_ns` | `float64` | 0 | 0.0% | 1 | 0.15 | 0.15 | 0.15 |
| `pd_num_routing_layers` | `int64` | 0 | 0.0% | 2 | 0.00 | 6.00 | 3.57 |
| `pd_is_sky130` | `int64` | 0 | 0.0% | 2 | 0.00 | 1.00 | 0.60 |
| `target_synthesis_runtime_s` | `float64` | 0 | 0.0% | 39 | 0.00 | 8.11 | 1.72 |
| `target_placement_runtime_s` | `float64` | 0 | 0.0% | 11 | 0.00 | 1.81 | 0.25 |
| `target_total_runtime_s` | `float64` | 0 | 0.0% | 40 | 0.52 | 9.98 | 2.43 |
| `target_cell_area_um2` | `float64` | 0 | 0.0% | 8 | 0.00 | 6715.00 | 1167.38 |
| `target_wns_ns` | `float64` | 0 | 0.0% | 3 | -2.76 | 7.06 | 1.28 |
| `target_tns_ns` | `float64` | 0 | 0.0% | 2 | -31.04 | 0.00 | -0.74 |
| `target_total_power_w` | `float64` | 0 | 0.0% | 3 | 0.00 | 0.00 | 0.00 |
| `target_total_wirelength_um` | `float64` | 0 | 0.0% | 1 | 0.00 | 0.00 | 0.00 |
| `target_routing_violations` | `float64` | 0 | 0.0% | 1 | 0.00 | 0.00 | 0.00 |
| `is_missing_timing` | `int64` | 0 | 0.0% | 2 | 0.00 | 1.00 | 0.79 |
| `is_missing_power` | `int64` | 0 | 0.0% | 2 | 0.00 | 1.00 | 0.79 |
| `is_missing_wirelength` | `int64` | 0 | 0.0% | 1 | 1.00 | 1.00 | 1.00 |

## 2. Redundancy & Multicollinearity Findings (|r| >= 0.85)

Identified highly correlated pairs that should be pruned or regularized during model training:

| Feature 1 | Feature 2 | Pearson |r| | Physical Explanation |
|---|---|---|---|
| `netlist_sequential_cells` | `netlist_ff_count` | 1.0 | Structural collinearity in design scale |
| `pd_num_routing_layers` | `pd_is_sky130` | 1.0 | Structural collinearity in design scale |
| `is_missing_timing` | `is_missing_power` | 1.0 | Structural collinearity in design scale |
| `feat_seq_ratio` | `feat_ff_ratio` | 1.0 | Structural collinearity in design scale |
| `netlist_total_cells` | `feat_density_proxy` | 0.9999 | Structural collinearity in design scale |
| `rtl_source_lines` | `rtl_code_lines` | 0.9998 | Structural collinearity in design scale |
| `log_rtl_source_lines` | `log_rtl_code_lines` | 0.9998 | Structural collinearity in design scale |
| `log_netlist_total_cells` | `log_total_nets` | 0.9998 | Structural collinearity in design scale |
| `netlist_total_cells` | `total_nets` | 0.9996 | Structural collinearity in design scale |
| `total_nets` | `feat_density_proxy` | 0.9995 | Structural collinearity in design scale |
| `log_netlist_total_cells` | `log_netlist_combinational_cells` | 0.9986 | Structural collinearity in design scale |
| `netlist_buffer_count` | `gate_count_aoi` | 0.9985 | Structural collinearity in design scale |

## 3. Zero-Leakage Dataset Splitting Strategy

To prevent data leakage, runs are partitioned strictly by RTL design family:

- **Train Partition:** 35 runs (83.3%) — Designs: `alu, booth_multiplier, fifo_sync, uart_tx`
- **Validation Partition:** 2 runs (4.8%) — Designs: `priority_encoder`
- **Test Partition:** 5 runs (11.9%) — Designs: `fsm_traffic`

> **Leakage Verification:** No overlapping designs exist across partitions (Train ∩ Val = ∅, Train ∩ Test = ∅, Val ∩ Test = ∅).
