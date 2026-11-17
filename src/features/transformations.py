"""Feature transformations, domain ratios, scaling, and normalization."""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler, RobustScaler


class FeatureTransformer:
    """Transforms raw RTL, netlist, and config features into normalized ML-ready matrices."""

    def __init__(self, use_robust_scaler: bool = False):
        self.scaler = RobustScaler() if use_robust_scaler else StandardScaler()
        self.fitted = False
        self.feature_names_: List[str] = []

    def compute_domain_interactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer domain-specific semiconductor and EDA ratio features."""
        df_out = df.copy()

        # Sequential vs Combinational Ratios
        total_c = np.maximum(df_out["netlist_total_cells"], 1)
        df_out["feat_seq_ratio"] = df_out["netlist_sequential_cells"] / total_c
        df_out["feat_comb_ratio"] = df_out["netlist_combinational_cells"] / total_c
        df_out["feat_ff_ratio"] = df_out["netlist_ff_count"] / total_c

        # Clock Frequency & Period interactions
        clk_p = np.maximum(df_out["pd_clock_period_ns"], 0.1)
        df_out["feat_clock_freq_mhz"] = 1000.0 / clk_p

        # Gate Complexity & Fanout Interaction
        df_out["feat_fanout_intensity"] = df_out["net_fanout_mean"] * np.log1p(df_out["net_fanout_max"])
        df_out["feat_depth_per_cell"] = df_out["netlist_estimated_logic_depth"] / np.log1p(total_c)

        # Logic density proxy
        util = np.clip(df_out["pd_target_utilization"], 0.05, 0.95)
        df_out["feat_density_proxy"] = total_c / util

        # Structural RTL to Netlist ratio
        rtl_lines = np.maximum(df_out["rtl_source_lines"], 1)
        df_out["feat_cells_per_rtl_line"] = total_c / rtl_lines

        return df_out

    def log_transform_skewed_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply log1p transformations to heavily skewed structural count features."""
        df_out = df.copy()
        skewed_cols = [
            "rtl_source_bytes", "rtl_source_lines", "rtl_code_lines",
            "netlist_total_cells", "netlist_combinational_cells", "netlist_sequential_cells",
            "gate_count_nand", "gate_count_nor", "gate_count_and", "gate_count_or",
            "gate_count_mux", "gate_count_aoi", "gate_count_oai", "total_nets",
            "target_cell_area_um2"
        ]

        for col in skewed_cols:
            if col in df_out.columns:
                df_out[f"log_{col}"] = np.log1p(np.maximum(df_out[col], 0))

        return df_out

    def fit_transform(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fit scaler on continuous features and return normalized DataFrame along with original."""
        df_eng = self.compute_domain_interactions(df)
        df_eng = self.log_transform_skewed_features(df_eng)

        # Identify numerical input feature columns (excluding identifiers and target variables)
        if feature_cols is None:
            exclude_prefixes = ("target_", "run_id", "design_name", "original_design_name", "run_status", "target_pdk")
            numeric_cols = [
                c for c in df_eng.columns
                if not any(c.startswith(p) for p in exclude_prefixes)
                and pd.api.types.is_numeric_dtype(df_eng[c])
            ]
        else:
            numeric_cols = feature_cols

        self.feature_names_ = numeric_cols

        # Fit and scale
        scaled_mat = self.scaler.fit_transform(df_eng[numeric_cols].fillna(0))
        self.fitted = True

        df_scaled = df_eng.copy()
        df_scaled[numeric_cols] = scaled_mat

        return df_eng, df_scaled

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform new data using fitted scaler."""
        if not self.fitted:
            raise RuntimeError("FeatureTransformer must be fitted before calling transform()")

        df_eng = self.compute_domain_interactions(df)
        df_eng = self.log_transform_skewed_features(df_eng)

        scaled_mat = self.scaler.transform(df_eng[self.feature_names_].fillna(0))
        df_scaled = df_eng.copy()
        df_scaled[self.feature_names_] = scaled_mat

        return df_scaled
