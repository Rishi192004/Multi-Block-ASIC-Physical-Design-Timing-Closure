"""Exploratory data analysis, correlation calculation, and multicollinearity identification."""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np


class DatasetAnalyzer:
    """Analyzes feature distributions, correlations with EDA targets, and multicollinearity."""

    def __init__(self, corr_threshold: float = 0.85):
        self.corr_threshold = corr_threshold

    def compute_data_quality_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess missingness, uniqueness, cardinality, and data integrity."""
        total_rows = len(df)
        quality = {
            "total_records": total_rows,
            "total_columns": len(df.columns),
            "columns": {}
        }

        for col in df.columns:
            n_null = int(df[col].isnull().sum())
            n_unique = int(df[col].nunique())
            dtype_str = str(df[col].dtype)

            col_stats = {
                "dtype": dtype_str,
                "null_count": n_null,
                "null_pct": round(n_null / total_rows * 100, 2),
                "unique_count": n_unique,
                "is_constant": (n_unique <= 1),
            }

            if pd.api.types.is_numeric_dtype(df[col]):
                valid_vals = df[col].dropna()
                if len(valid_vals) > 0:
                    col_stats["min"] = float(valid_vals.min())
                    col_stats["max"] = float(valid_vals.max())
                    col_stats["mean"] = round(float(valid_vals.mean()), 4)
                    col_stats["std"] = round(float(valid_vals.std()), 4) if len(valid_vals) > 1 else 0.0

            quality["columns"][col] = col_stats

        return quality

    def compute_target_correlations(
        self,
        df: pd.DataFrame,
        targets: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Compute Pearson and Spearman correlations between numeric features and EDA targets."""
        target_cols = targets or [
            "target_synthesis_runtime_s",
            "target_placement_runtime_s",
            "target_total_runtime_s",
            "target_cell_area_um2",
            "target_wns_ns"
        ]
        target_cols = [t for t in target_cols if t in df.columns]

        numeric_df = df.select_dtypes(include=[np.number])
        feature_cols = [c for c in numeric_df.columns if not c.startswith("target_") and not c.startswith("is_")]

        corr_matrix = numeric_df.corr(method="pearson")
        target_corr = corr_matrix.loc[feature_cols, target_cols]

        return target_corr.sort_values(by=target_cols[0], ascending=False)

    def identify_highly_correlated_pairs(
        self,
        df: pd.DataFrame,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Identify redundant feature pairs with absolute correlation above threshold."""
        thresh = threshold or self.corr_threshold
        numeric_df = df.select_dtypes(include=[np.number])
        feature_cols = [c for c in numeric_df.columns if not c.startswith("target_")]
        
        corr_matrix = numeric_df[feature_cols].corr().abs()

        pairs = []
        for i in range(len(feature_cols)):
            for j in range(i + 1, len(feature_cols)):
                c1 = feature_cols[i]
                c2 = feature_cols[j]
                val = corr_matrix.loc[c1, c2]
                if not np.isnan(val) and val >= thresh:
                    pairs.append({
                        "feature_1": c1,
                        "feature_2": c2,
                        "correlation": round(float(val), 4)
                    })

        pairs.sort(key=lambda x: x["correlation"], reverse=True)
        return pairs
