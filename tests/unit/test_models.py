"""Unit tests for predictive modeling engine, metrics, registry, and inference."""

import pytest
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from src.models.metrics import compute_mape, evaluate_predictions
from src.models.registry import ModelRegistry, ModelMetadata
from src.models.train import ModelTrainer
from src.models.inference import EDAPredictor, PredictionResult


# -------------------------------------------------------------------------
# 1. Metrics Tests
# -------------------------------------------------------------------------
def test_compute_mape_zero_handling():
    """compute_mape must not divide by zero or return inf/nan when y_true has zeros."""
    y_true = np.array([0.0, 0.0, 10.0, 20.0])
    y_pred = np.array([0.1, 0.0, 11.0, 19.0])

    mape = compute_mape(y_true, y_pred, epsilon=1e-3)
    assert not np.isnan(mape)
    assert not np.isinf(mape)
    assert mape >= 0.0


def test_evaluate_predictions_perfect():
    """evaluate_predictions must return R2=1.0 and MAE=0.0 for perfect predictions."""
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    metrics = evaluate_predictions(y, y)

    assert metrics["r2"] == 1.0
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["mape"] == 0.0


def test_evaluate_predictions_residual_bias():
    """evaluate_predictions must accurately measure positive/negative bias."""
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([12.0, 22.0])  # +2.0 over-prediction bias
    metrics = evaluate_predictions(y_true, y_pred)

    assert metrics["bias"] == 2.0
    assert metrics["mae"] == 2.0


# -------------------------------------------------------------------------
# 2. Model Registry Tests
# -------------------------------------------------------------------------
def test_model_registry_save_load(tmp_path):
    registry = ModelRegistry(base_dir=tmp_path / "models")
    model = Ridge(alpha=1.0)
    X = np.array([[1.0, 2.0], [3.0, 4.0]])
    y = np.array([5.0, 7.0])
    model.fit(X, y)

    metadata = ModelMetadata(
        model_name="ridge_test",
        target_name="runtime_test",
        version="v_test",
        feature_names=["f1", "f2"],
        training_metrics={"r2": 0.99},
        feature_bounds={"f1": {"min": 1.0, "max": 3.0, "mean": 2.0, "std": 1.0}}
    )

    saved_dir = registry.save_model(model, metadata)
    assert saved_dir.exists()
    assert (saved_dir / "model.joblib").exists()
    assert (saved_dir / "metadata.json").exists()

    loaded_m, loaded_meta, _ = registry.load_model("v_test", "runtime_test", "ridge_test")
    assert loaded_meta.model_name == "ridge_test"
    pred = loaded_m.predict([[2.0, 3.0]])
    assert len(pred) == 1


# -------------------------------------------------------------------------
# 3. Model Trainer Tests
# -------------------------------------------------------------------------
def test_model_trainer_group_cv(tmp_path):
    registry = ModelRegistry(base_dir=tmp_path / "models")
    trainer = ModelTrainer(registry=registry, version="test")

    # Synthetic multi-design dataset
    designs = ["d1", "d2", "d3"]
    rows = []
    for d in designs:
        for i in range(4):
            c_count = np.random.uniform(50, 500)
            rows.append({
                "design_name": d,
                "netlist_total_cells": c_count,
                "rtl_source_lines": c_count * 0.1,
                "target_runtime": c_count * 0.01 + 0.5
            })

    train_df = pd.DataFrame(rows[:8])
    test_df = pd.DataFrame(rows[8:])

    res = trainer.train_and_benchmark_target(
        train_df=train_df,
        test_df=test_df,
        target_col="target_runtime",
        group_col="design_name"
    )

    assert "best_model" in res
    assert res["best_model"] in ("linear_regression", "random_forest", "gradient_boosting", "xgboost")
    assert "models" in res
    assert len(res["models"]) == 4


# -------------------------------------------------------------------------
# 4. Inference & OOD Detection Tests
# -------------------------------------------------------------------------
def test_eda_predictor_ood_detection(tmp_path):
    registry = ModelRegistry(base_dir=tmp_path / "models")
    predictor = EDAPredictor(registry=registry, version="test")

    bounds = {
        "netlist_total_cells": {"min": 100.0, "max": 1000.0, "mean": 500.0, "std": 100.0}
    }

    # In-distribution sample
    in_dist_series = pd.Series({"netlist_total_cells": 600.0})
    is_ood, ood_cols, score = predictor.check_ood(in_dist_series, bounds)
    assert not is_ood
    assert len(ood_cols) == 0

    # Out-of-distribution sample (vastly exceeds max + 3*std)
    ood_series = pd.Series({"netlist_total_cells": 50000.0})
    is_ood, ood_cols, score = predictor.check_ood(ood_series, bounds)
    assert is_ood
    assert len(ood_cols) >= 1
    assert "netlist_total_cells" in ood_cols[0]
