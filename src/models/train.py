"""Training pipeline benchmarking Linear Regression, Random Forest, Gradient Boosting, and XGBoost."""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import LeaveOneGroupOut, GroupKFold

from src.models.metrics import evaluate_predictions
from src.models.registry import ModelRegistry, ModelMetadata
from src.common.logger import logger


CANDIDATE_MODELS = {
    "linear_regression": lambda: Ridge(alpha=1.0, random_state=42),
    "random_forest": lambda: RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42),
    "gradient_boosting": lambda: GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42),
    "xgboost": lambda: xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42, n_jobs=1),
}


class ModelTrainer:
    """Orchestrates cross-validated model training, benchmarking, and selection."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        version: str = "v1"
    ):
        self.registry = registry or ModelRegistry()
        self.version = version

    def prepare_feature_matrix(
        self,
        df: pd.DataFrame,
        target_col: str
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Filter out non-feature metadata and separate X and y."""
        exclude_prefixes = (
            "target_", "run_id", "design_name", "original_design_name",
            "run_status", "target_pdk", "is_missing_"
        )
        feature_cols = [
            c for c in df.columns
            if not any(c.startswith(p) for p in exclude_prefixes)
            and pd.api.types.is_numeric_dtype(df[c])
        ]

        X = df[feature_cols].copy().fillna(0.0).astype(float)
        y = df[target_col].copy().fillna(0.0).astype(float)
        return X, y, feature_cols

    def evaluate_group_cv(
        self,
        model_fn,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series
    ) -> Tuple[Dict[str, float], np.ndarray]:
        """Perform Leave-One-Group-Out cross-validation by design family."""
        logo = LeaveOneGroupOut()
        oof_preds = np.zeros(len(y))

        for train_idx, val_idx in logo.split(X, y, groups=groups):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_va = X.iloc[val_idx]
            
            m = model_fn()
            m.fit(X_tr, y_tr)
            oof_preds[val_idx] = m.predict(X_va)

        metrics = evaluate_predictions(y.values, oof_preds)
        return metrics, oof_preds

    def train_and_benchmark_target(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        target_col: str,
        group_col: str = "design_name"
    ) -> Dict[str, Any]:
        """Benchmark all 4 models on a single target outcome using grouped CV and held-out test."""
        logger.info(f"--- Training & Benchmarking for Target: [{target_col}] ---")

        X_train, y_train, feature_cols = self.prepare_feature_matrix(train_df, target_col)
        X_test, y_test, _ = self.prepare_feature_matrix(test_df, target_col)
        groups = train_df[group_col]

        # Calculate training feature bounds for out-of-distribution detection
        bounds = {}
        for col in feature_cols:
            bounds[col] = {
                "min": float(X_train[col].min()),
                "max": float(X_train[col].max()),
                "mean": float(X_train[col].mean()),
                "std": float(X_train[col].std()) if len(X_train) > 1 else 0.0
            }

        benchmark_results = {}
        best_model_name = None
        lowest_cv_mae = float("inf")
        best_model_instance = None
        best_metadata = None

        for model_name, model_fn in CANDIDATE_MODELS.items():
            # 1. Group-CV evaluation (Out-of-Fold across design families)
            cv_metrics, oof_preds = self.evaluate_group_cv(model_fn, X_train, y_train, groups=groups)

            # 2. Fit full model on all training data
            full_model = model_fn()
            full_model.fit(X_train, y_train)
            train_preds = full_model.predict(X_train)
            train_metrics = evaluate_predictions(y_train.values, train_preds)

            # 3. Evaluate on held-out test partition (unseen design family)
            test_preds = full_model.predict(X_test)
            test_metrics = evaluate_predictions(y_test.values, test_preds)

            # Per-design breakdown on test partition
            test_df_eval = test_df.copy()
            test_df_eval["y_true"] = y_test.values
            test_df_eval["y_pred"] = test_preds
            design_errors = {}
            for d_name, d_grp in test_df_eval.groupby(group_col):
                design_errors[d_name] = evaluate_predictions(d_grp["y_true"].values, d_grp["y_pred"].values)

            benchmark_results[model_name] = {
                "train_metrics": train_metrics,
                "cv_metrics": cv_metrics,
                "test_metrics": test_metrics,
                "design_test_errors": design_errors
            }

            logger.info(
                f"[{model_name}] CV MAE: {cv_metrics['mae']:.3f} | Test MAE: {test_metrics['mae']:.3f} | Test R2: {test_metrics['r2']:.3f}"
            )

            # Model selection: prioritize lowest out-of-fold Group-CV MAE
            if cv_metrics["mae"] < lowest_cv_mae:
                lowest_cv_mae = cv_metrics["mae"]
                best_model_name = model_name
                best_model_instance = full_model
                best_metadata = ModelMetadata(
                    model_name=model_name,
                    target_name=target_col,
                    version=self.version,
                    feature_names=feature_cols,
                    training_metrics=train_metrics,
                    cv_metrics=cv_metrics,
                    test_metrics=test_metrics,
                    feature_bounds=bounds,
                    train_designs=sorted(list(train_df[group_col].unique())),
                    test_designs=sorted(list(test_df[group_col].unique())),
                    hyperparameters={"n_features": len(feature_cols)}
                )

        # Save the champion model to registry
        if best_model_instance and best_metadata:
            saved_dir = self.registry.save_model(best_model_instance, best_metadata)
            logger.info(f"Champion model [{best_model_name}] for [{target_col}] saved to: {saved_dir}")

        return {
            "target": target_col,
            "best_model": best_model_name,
            "models": benchmark_results,
            "feature_cols": feature_cols
        }
