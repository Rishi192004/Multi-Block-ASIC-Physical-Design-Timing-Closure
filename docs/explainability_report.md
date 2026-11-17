# EDA-Genius: Model Explainability & Residual Analysis Report

Documenting global feature importance, SHAP contributions, and design-family error breakdowns.

## Target: `synthesis_runtime_s` (Champion: `random_forest`)

### Top 10 Most Influential Features

| Rank | Feature Name | Normalized Importance (%) | Physical Role in Semiconductor EDA |
|---|---|---|---|
| 1 | `log_target_cell_area_um2` | 63.69% | Standard cell structural complexity predictor |
| 2 | `feat_cells_per_rtl_line` | 11.61% | Standard cell structural complexity predictor |
| 3 | `log_netlist_combinational_cells` | 2.41% | Standard cell structural complexity predictor |
| 4 | `log_gate_count_or` | 2.01% | Standard cell structural complexity predictor |
| 5 | `netlist_inverter_count` | 1.31% | Standard cell structural complexity predictor |
| 6 | `log_gate_count_oai` | 1.11% | Standard cell structural complexity predictor |
| 7 | `log_gate_count_aoi` | 1.10% | Standard cell structural complexity predictor |
| 8 | `feat_clock_freq_mhz` | 1.09% | Standard cell structural complexity predictor |
| 9 | `pd_num_routing_layers` | 1.08% | Standard cell structural complexity predictor |
| 10 | `netlist_combinational_cells` | 1.03% | Standard cell structural complexity predictor |

### Design-Family Error Breakdown (Held-Out Test)

| Design Family | Sample Count | Actual Mean | Predicted Mean | MAE | Mean Bias |
|---|---|---|---|---|---|
| `fsm_traffic` | 5 | 1.076 | 1.068 | 0.165 | -0.007 |

### Visualizations Generated

- **Pred Vs Actual:** `artifacts\models\v1\plots\pred_vs_actual_synthesis_runtime_s.png`
- **Residuals:** `artifacts\models\v1\plots\residuals_synthesis_runtime_s.png`
- **Feature Importance:** `artifacts\models\v1\plots\feature_importance_synthesis_runtime_s.png`

---

## Target: `placement_runtime_s` (Champion: `xgboost`)

### Top 10 Most Influential Features

| Rank | Feature Name | Normalized Importance (%) | Physical Role in Semiconductor EDA |
|---|---|---|---|
| 1 | `gate_count_and` | 57.48% | Standard cell structural complexity predictor |
| 2 | `feat_seq_ratio` | 15.77% | Standard cell structural complexity predictor |
| 3 | `pd_target_utilization` | 8.57% | Standard cell structural complexity predictor |
| 4 | `is_success` | 8.07% | Standard cell structural complexity predictor |
| 5 | `log_target_cell_area_um2` | 7.38% | Standard cell structural complexity predictor |
| 6 | `rtl_num_inputs` | 2.65% | Standard cell structural complexity predictor |
| 7 | `pd_clock_period_ns` | 0.07% | Standard cell structural complexity predictor |
| 8 | `netlist_total_cells` | 0.00% | Standard cell structural complexity predictor |
| 9 | `rtl_num_ports` | 0.00% | Standard cell structural complexity predictor |
| 10 | `rtl_num_outputs` | 0.00% | Standard cell structural complexity predictor |

### Design-Family Error Breakdown (Held-Out Test)

| Design Family | Sample Count | Actual Mean | Predicted Mean | MAE | Mean Bias |
|---|---|---|---|---|---|
| `fsm_traffic` | 5 | 0.0 | 0.003 | 0.003 | 0.003 |

### Visualizations Generated

- **Pred Vs Actual:** `artifacts\models\v1\plots\pred_vs_actual_placement_runtime_s.png`
- **Residuals:** `artifacts\models\v1\plots\residuals_placement_runtime_s.png`
- **Feature Importance:** `artifacts\models\v1\plots\feature_importance_placement_runtime_s.png`

---

## Target: `total_runtime_s` (Champion: `gradient_boosting`)

### Top 10 Most Influential Features

| Rank | Feature Name | Normalized Importance (%) | Physical Role in Semiconductor EDA |
|---|---|---|---|
| 1 | `log_target_cell_area_um2` | 81.38% | Standard cell structural complexity predictor |
| 2 | `pd_num_routing_layers` | 5.24% | Standard cell structural complexity predictor |
| 3 | `pd_is_sky130` | 4.51% | Standard cell structural complexity predictor |
| 4 | `is_success` | 1.13% | Standard cell structural complexity predictor |
| 5 | `feat_density_proxy` | 1.07% | Standard cell structural complexity predictor |
| 6 | `pd_target_utilization` | 0.65% | Standard cell structural complexity predictor |
| 7 | `feat_clock_freq_mhz` | 0.51% | Standard cell structural complexity predictor |
| 8 | `netlist_total_cells` | 0.41% | Standard cell structural complexity predictor |
| 9 | `pd_clock_period_ns` | 0.39% | Standard cell structural complexity predictor |
| 10 | `rtl_num_registers` | 0.39% | Standard cell structural complexity predictor |

### Design-Family Error Breakdown (Held-Out Test)

| Design Family | Sample Count | Actual Mean | Predicted Mean | MAE | Mean Bias |
|---|---|---|---|---|---|
| `fsm_traffic` | 5 | 1.491 | 1.524 | 0.258 | 0.032 |

### Visualizations Generated

- **Pred Vs Actual:** `artifacts\models\v1\plots\pred_vs_actual_total_runtime_s.png`
- **Residuals:** `artifacts\models\v1\plots\residuals_total_runtime_s.png`
- **Feature Importance:** `artifacts\models\v1\plots\feature_importance_total_runtime_s.png`

---

## Target: `cell_area_um2` (Champion: `gradient_boosting`)

### Top 10 Most Influential Features

| Rank | Feature Name | Normalized Importance (%) | Physical Role in Semiconductor EDA |
|---|---|---|---|
| 1 | `log_target_cell_area_um2` | 53.56% | Standard cell structural complexity predictor |
| 2 | `net_fanout_max` | 9.51% | Standard cell structural complexity predictor |
| 3 | `log_gate_count_or` | 8.19% | Standard cell structural complexity predictor |
| 4 | `log_netlist_combinational_cells` | 7.42% | Standard cell structural complexity predictor |
| 5 | `feat_cells_per_rtl_line` | 5.38% | Standard cell structural complexity predictor |
| 6 | `is_success` | 5.05% | Standard cell structural complexity predictor |
| 7 | `gate_count_mux` | 2.56% | Standard cell structural complexity predictor |
| 8 | `netlist_total_cells` | 2.22% | Standard cell structural complexity predictor |
| 9 | `log_gate_count_mux` | 0.95% | Standard cell structural complexity predictor |
| 10 | `log_gate_count_nor` | 0.68% | Standard cell structural complexity predictor |

### Design-Family Error Breakdown (Held-Out Test)

| Design Family | Sample Count | Actual Mean | Predicted Mean | MAE | Mean Bias |
|---|---|---|---|---|---|
| `fsm_traffic` | 5 | 165.6 | 296.808 | 131.208 | 131.208 |

### Visualizations Generated

- **Pred Vs Actual:** `artifacts\models\v1\plots\pred_vs_actual_cell_area_um2.png`
- **Residuals:** `artifacts\models\v1\plots\residuals_cell_area_um2.png`
- **Feature Importance:** `artifacts\models\v1\plots\feature_importance_cell_area_um2.png`

---

## Target: `wns_ns` (Champion: `random_forest`)

### Top 10 Most Influential Features

| Rank | Feature Name | Normalized Importance (%) | Physical Role in Semiconductor EDA |
|---|---|---|---|
| 1 | `log_target_cell_area_um2` | 22.80% | Standard cell structural complexity predictor |
| 2 | `feat_seq_ratio` | 15.19% | Standard cell structural complexity predictor |
| 3 | `feat_clock_freq_mhz` | 10.25% | Standard cell structural complexity predictor |
| 4 | `pd_clock_period_ns` | 9.74% | Standard cell structural complexity predictor |
| 5 | `feat_ff_ratio` | 9.34% | Standard cell structural complexity predictor |
| 6 | `feat_density_proxy` | 5.02% | Standard cell structural complexity predictor |
| 7 | `pd_target_utilization` | 4.29% | Standard cell structural complexity predictor |
| 8 | `log_gate_count_and` | 2.43% | Standard cell structural complexity predictor |
| 9 | `is_success` | 2.26% | Standard cell structural complexity predictor |
| 10 | `net_fanout_mean` | 2.12% | Standard cell structural complexity predictor |

### Design-Family Error Breakdown (Held-Out Test)

| Design Family | Sample Count | Actual Mean | Predicted Mean | MAE | Mean Bias |
|---|---|---|---|---|---|
| `fsm_traffic` | 5 | 0.0 | 0.424 | 0.424 | 0.424 |

### Visualizations Generated

- **Pred Vs Actual:** `artifacts\models\v1\plots\pred_vs_actual_wns_ns.png`
- **Residuals:** `artifacts\models\v1\plots\residuals_wns_ns.png`
- **Feature Importance:** `artifacts\models\v1\plots\feature_importance_wns_ns.png`

---

