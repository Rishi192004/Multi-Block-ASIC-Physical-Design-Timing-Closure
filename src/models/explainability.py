"""Model explainability: feature importance, SHAP values, residual analysis, and plots."""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend for server/CLI
import matplotlib.pyplot as plt
import shap
from src.common.logger import logger


class ModelExplainer:
    """Generates feature importance rankings, SHAP values, residual plots, and error breakdowns."""

    def __init__(self, output_dir: Path = Path("artifacts/models/v1/plots")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compute_feature_importance(
        self,
        model: Any,
        feature_names: List[str]
    ) -> pd.DataFrame:
        """Extract normalized feature importance scores from linear or tree-based models."""
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.abs(model.coef_)
        else:
            return pd.DataFrame()

        df_imp = pd.DataFrame({
            "feature": feature_names,
            "importance": importances
        }).sort_values(by="importance", ascending=False).reset_index(drop=True)

        total = df_imp["importance"].sum()
        if total > 0:
            df_imp["normalized_pct"] = (df_imp["importance"] / total) * 100.0
        else:
            df_imp["normalized_pct"] = 0.0

        return df_imp

    def compute_shap_explanations(
        self,
        model: Any,
        X: pd.DataFrame,
        top_k: int = 15
    ) -> pd.DataFrame:
        """Calculate global mean absolute SHAP values."""
        try:
            X_clean = X.copy().astype(float)
            explainer = shap.Explainer(model, X_clean)
            shap_values = explainer(X_clean)
            vals = np.abs(shap_values.values).mean(axis=0)

            df_shap = pd.DataFrame({
                "feature": X_clean.columns,
                "mean_abs_shap": vals
            }).sort_values(by="mean_abs_shap", ascending=False).head(top_k).reset_index(drop=True)
            return df_shap
        except Exception as e:
            logger.warning(f"SHAP explanation computation fell back to permutation/importance: {e}")
            return pd.DataFrame()

    def generate_plots(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        target_name: str,
        model_name: str,
        feature_importance_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Path]:
        """Generate and save Predicted-vs-Actual, Residual distribution, and Feature Importance plots."""
        saved_plots = {}
        clean_target = target_name.replace("target_", "")

        # 1. Predicted vs Actual Plot
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(y_true, y_pred, alpha=0.7, edgecolors="k", color="#2b5c8f")
        
        min_v = min(np.min(y_true), np.min(y_pred))
        max_v = max(np.max(y_true), np.max(y_pred))
        ax.plot([min_v, max_v], [min_v, max_v], "r--", label="Ideal 1:1")
        
        ax.set_title(f"Predicted vs Actual: {clean_target}\n({model_name})", fontsize=11, fontweight="bold")
        ax.set_xlabel("Actual Value", fontsize=10)
        ax.set_ylabel("Predicted Value", fontsize=10)
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)
        
        pv_path = self.output_dir / f"pred_vs_actual_{clean_target}.png"
        fig.tight_layout()
        fig.savefig(pv_path, dpi=150)
        plt.close(fig)
        saved_plots["pred_vs_actual"] = pv_path

        # 2. Residual Distribution Plot
        residuals = y_pred - y_true
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(residuals, bins=15, color="#388e3c", edgecolor="black", alpha=0.7)
        ax.axvline(0, color="red", linestyle="--", label="Zero Residual")
        ax.set_title(f"Residual Distribution: {clean_target}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Residual (Predicted - Actual)", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)

        res_path = self.output_dir / f"residuals_{clean_target}.png"
        fig.tight_layout()
        fig.savefig(res_path, dpi=150)
        plt.close(fig)
        saved_plots["residuals"] = res_path

        # 3. Feature Importance Bar Plot
        if feature_importance_df is not None and not feature_importance_df.empty:
            top_features = feature_importance_df.head(10).iloc[::-1]
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.barh(top_features["feature"], top_features["importance"], color="#d35400", alpha=0.85)
            ax.set_title(f"Top 10 Features: {clean_target} ({model_name})", fontsize=11, fontweight="bold")
            ax.set_xlabel("Feature Importance", fontsize=10)
            ax.grid(True, axis="x", linestyle="--", alpha=0.6)

            imp_path = self.output_dir / f"feature_importance_{clean_target}.png"
            fig.tight_layout()
            fig.savefig(imp_path, dpi=150)
            plt.close(fig)
            saved_plots["feature_importance"] = imp_path

        return saved_plots

    def analyze_residuals_by_design(
        self,
        df_eval: pd.DataFrame,
        target_name: str,
        group_col: str = "design_name"
    ) -> pd.DataFrame:
        """Compute residual metrics broken down by individual design family."""
        records = []
        for d_name, grp in df_eval.groupby(group_col):
            y_t = grp[target_name].values
            y_p = grp["y_pred"].values
            res = y_p - y_t
            records.append({
                "design_name": d_name,
                "samples": len(grp),
                "actual_mean": round(float(np.mean(y_t)), 3),
                "pred_mean": round(float(np.mean(y_p)), 3),
                "mae": round(float(np.mean(np.abs(res))), 3),
                "mean_bias": round(float(np.mean(res)), 3),
                "max_abs_err": round(float(np.max(np.abs(res))), 3)
            })

        return pd.DataFrame(records).sort_values(by="mae", ascending=False).reset_index(drop=True)
