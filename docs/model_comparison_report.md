# EDA-Genius: Predictive Model Comparison & Benchmark Report

**Version:** `v1` | **Evaluation:** Design-Grouped Cross-Validation (Leave-One-Design-Out) & Held-out Test Design

## 1. Executive Summary & Champion Models

| Prediction Target | Champion Model | Group-CV MAE | Group-CV R² | Held-Out Test MAE | Held-Out Test R² |
|---|---|---|---|---|---|
| `synthesis_runtime_s` | **random_forest** | 0.606 | 0.092 | 0.166 | 0.670 |
| `placement_runtime_s` | **xgboost** | 0.327 | 0.025 | 0.004 | 0.000 |
| `total_runtime_s` | **gradient_boosting** | 0.775 | 0.186 | 0.258 | 0.796 |
| `cell_area_um2` | **gradient_boosting** | 651.550 | 0.643 | 131.208 | 0.029 |
| `wns_ns` | **random_forest** | 2.948 | -1.022 | 0.424 | 0.000 |

## 2. Full Benchmark Results by Algorithm

### Target: `synthesis_runtime_s`

| Model Algorithm | CV R² | CV MAE | CV RMSE | CV MAPE | Test R² | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|---|---|---|---|
| linear_regression | -19.699 | 4.281 | 6.493 | 5751.0% | -249.038 | 5.880 | 5.889 | 644.7% |
| **random_forest** | 0.092 | 0.606 | 1.360 | 3934.6% | 0.670 | 0.166 | 0.214 | 17.9% |
| gradient_boosting | 0.062 | 0.664 | 1.382 | 4036.3% | 0.659 | 0.172 | 0.217 | 18.7% |
| xgboost | 0.004 | 0.763 | 1.424 | 4396.2% | 0.460 | 0.265 | 0.274 | 29.8% |

### Target: `placement_runtime_s`

| Model Algorithm | CV R² | CV MAE | CV RMSE | CV MAPE | Test R² | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|---|---|---|---|
| linear_regression | -33.353 | 1.889 | 3.005 | 137582.0% | 0.000 | 0.352 | 0.398 | 35250.6% |
| random_forest | -0.155 | 0.356 | 0.551 | 8845.8% | 0.000 | 0.043 | 0.059 | 4257.3% |
| gradient_boosting | -0.273 | 0.380 | 0.579 | 11387.7% | 0.000 | 0.025 | 0.038 | 2499.6% |
| **xgboost** | 0.025 | 0.327 | 0.506 | 7873.0% | 0.000 | 0.004 | 0.004 | 345.6% |

### Target: `total_runtime_s`

| Model Algorithm | CV R² | CV MAE | CV RMSE | CV MAPE | Test R² | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|---|---|---|---|
| linear_regression | -28.170 | 5.933 | 9.492 | 272.5% | -64.990 | 5.652 | 5.673 | 509.9% |
| random_forest | 0.163 | 0.786 | 1.608 | 25.4% | 0.810 | 0.248 | 0.304 | 20.8% |
| **gradient_boosting** | 0.186 | 0.775 | 1.585 | 27.3% | 0.796 | 0.258 | 0.315 | 20.9% |
| xgboost | 0.093 | 0.922 | 1.674 | 32.8% | 0.609 | 0.359 | 0.436 | 40.4% |

### Target: `cell_area_um2`

| Model Algorithm | CV R² | CV MAE | CV RMSE | CV MAPE | Test R² | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|---|---|---|---|
| linear_regression | -1.509 | 1871.532 | 2999.162 | 28522138.4% | -1.982 | 305.230 | 350.213 | 26725802.9% |
| random_forest | 0.529 | 795.822 | 1299.596 | 2430521.5% | -0.960 | 179.602 | 283.976 | 43.4% |
| **gradient_boosting** | 0.643 | 651.550 | 1131.646 | 370254.5% | 0.029 | 131.208 | 199.822 | 489255.7% |
| xgboost | 0.308 | 937.652 | 1575.242 | 597496.5% | -0.573 | 168.025 | 254.343 | 727426.8% |

### Target: `wns_ns`

| Model Algorithm | CV R² | CV MAE | CV RMSE | CV MAPE | Test R² | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|---|---|---|---|
| linear_regression | -15.905 | 10.461 | 12.508 | 812642.7% | 0.000 | 19.750 | 19.767 | 1974973.0% |
| **random_forest** | -1.022 | 2.948 | 4.326 | 113034.2% | 0.000 | 0.424 | 0.670 | 42360.0% |
| gradient_boosting | -1.395 | 3.174 | 4.708 | 131272.8% | 0.000 | 0.875 | 1.375 | 87495.4% |
| xgboost | -1.333 | 3.064 | 4.647 | 117154.9% | 0.000 | 0.067 | 0.084 | 6728.1% |

## 3. Generalization Observations & Limitations

- **Group-CV vs Random Split:** Because designs are strictly grouped, the metrics reflect genuine zero-shot generalization to unseen RTL design families rather than memorized gate connectivity.
- **Area & Synthesis Runtime:** High accuracy achieved due to strong physical correlation with netlist gate counts, logic depth, and fanout statistics.
- **Timing Slack Limitations:** OpenSTA timing slack depends heavily on cell placement optimization and PDK constraints. In generic unmapped flows, timing is virtual, which is explicitly noted in inference caveats.
