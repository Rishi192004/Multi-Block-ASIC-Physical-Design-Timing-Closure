"""Inference engine with out-of-distribution (OOD) checks and confidence scoring."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from src.models.registry import ModelRegistry, ModelMetadata
from src.features.rtl_extractor import RTLExtractor
from src.features.netlist_extractor import NetlistExtractor
from src.features.config_extractor import ConfigExtractor
from src.features.transformations import FeatureTransformer
from src.common.logger import logger


class PredictionResult(BaseModel):
    """Container for individual target predictions with confidence and OOD flags."""
    target_name: str
    predicted_value: float
    unit: str
    model_name: str
    model_version: str
    confidence_level: str  # 'HIGH', 'MEDIUM', 'LOW_OOD'
    is_out_of_distribution: bool
    ood_features: List[str] = Field(default_factory=list)
    caveats: Optional[str] = None


class ComprehensivePrediction(BaseModel):
    """Aggregate predictions covering EDA runtime and physical design PPA outcomes."""
    design_name: str
    synthesis_runtime_s: PredictionResult
    placement_runtime_s: PredictionResult
    total_runtime_s: PredictionResult
    cell_area_um2: PredictionResult
    timing_wns_ns: PredictionResult
    overall_ood_score: float  # fraction of features exceeding training bounds
    recommendations: List[str] = Field(default_factory=list)


class EDAPredictor:
    """Production inference API with feature alignment, scaling, and OOD detection."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        version: str = "v1"
    ):
        self.registry = registry or ModelRegistry()
        self.version = version
        self.models: Dict[str, Any] = {}
        self.metadata: Dict[str, ModelMetadata] = {}
        self.scalers: Dict[str, Any] = {}

        self.rtl_extractor = RTLExtractor()
        self.netlist_extractor = NetlistExtractor()
        self.config_extractor = ConfigExtractor()
        self.transformer = FeatureTransformer()

    def load_champion_models(
        self,
        target_names: Optional[List[str]] = None
    ):
        """Load champion models for all prediction targets."""
        targets = target_names or [
            "target_synthesis_runtime_s",
            "target_placement_runtime_s",
            "target_total_runtime_s",
            "target_cell_area_um2",
            "target_wns_ns"
        ]

        target_base = self.registry.base_dir / self.version
        for target in targets:
            t_dir = target_base / target
            if not t_dir.exists():
                logger.warning(f"No models found for target: {target}")
                continue

            # Pick the first saved champion model in directory
            candidate_dirs = [d for d in t_dir.iterdir() if d.is_dir()]
            if not candidate_dirs:
                continue
            model_name = candidate_dirs[0].name

            try:
                m, meta, s = self.registry.load_model(self.version, target, model_name)
                self.models[target] = m
                self.metadata[target] = meta
                self.scalers[target] = s
                logger.info(f"Loaded champion [{model_name}] for [{target}]")
            except Exception as e:
                logger.error(f"Failed to load model for {target}: {e}")

    def check_ood(
        self,
        features: pd.Series,
        bounds: Dict[str, Dict[str, float]],
        std_threshold: float = 3.0
    ) -> Tuple[bool, List[str], float]:
        """Detect if input features fall outside training boundaries."""
        ood_features = []
        total_checked = 0

        for col, b in bounds.items():
            if col in features:
                total_checked += 1
                val = float(features[col])
                c_min = b.get("min", float("-inf"))
                c_max = b.get("max", float("inf"))
                c_std = b.get("std", 1.0)
                margin = max(c_std * std_threshold, 1e-4)

                if val < (c_min - margin) or val > (c_max + margin):
                    ood_features.append(f"{col} (val={val:.2f}, train_range=[{c_min:.2f}, {c_max:.2f}])")

        ood_score = len(ood_features) / max(total_checked, 1)
        is_ood = (ood_score > 0.05) or (len(ood_features) >= 3)
        return is_ood, ood_features, round(ood_score, 3)

    def predict_from_features(
        self,
        feature_dict: Dict[str, Any],
        design_name: str = "unnamed_design"
    ) -> ComprehensivePrediction:
        """Run inference on an engineered feature row."""
        if not self.models:
            self.load_champion_models()

        df_in = pd.DataFrame([feature_dict])
        df_eng = self.transformer.compute_domain_interactions(df_in)
        df_eng = self.transformer.log_transform_skewed_features(df_eng)
        feature_row = df_eng.iloc[0]

        predictions: Dict[str, PredictionResult] = {}
        all_ood_features = []

        units_map = {
            "target_synthesis_runtime_s": "seconds",
            "target_placement_runtime_s": "seconds",
            "target_total_runtime_s": "seconds",
            "target_cell_area_um2": "µm²",
            "target_wns_ns": "ns"
        }

        for target, model in self.models.items():
            meta = self.metadata[target]
            expected_cols = meta.feature_names

            # Align columns
            X = pd.DataFrame([{c: feature_row.get(c, 0.0) for c in expected_cols}])
            X = X.fillna(0.0)

            # Check Out-of-Distribution status
            is_ood, ood_cols, ood_score = self.check_ood(feature_row, meta.feature_bounds)
            if is_ood:
                all_ood_features.extend(ood_cols)
                conf = "LOW_OOD"
            elif ood_score > 0.0:
                conf = "MEDIUM"
            else:
                conf = "HIGH"

            # Predict
            pred_val = float(model.predict(X)[0])

            # Domain non-negativity clipping for physical metrics
            if "runtime" in target or "area" in target:
                pred_val = max(0.0, pred_val)

            caveat = None
            if target == "target_wns_ns":
                caveat = "Timing slack prediction is calibrated for SKY130 standard cells with OpenSTA; generic flows lack real parasitic modeling."

            predictions[target] = PredictionResult(
                target_name=target,
                predicted_value=round(pred_val, 4),
                unit=units_map.get(target, ""),
                model_name=meta.model_name,
                model_version=meta.version,
                confidence_level=conf,
                is_out_of_distribution=is_ood,
                ood_features=ood_cols,
                caveats=caveat
            )

        unique_ood = sorted(list(set(all_ood_features)))
        overall_ood = len(unique_ood) / max(len(feature_row), 1)

        recommendations = []
        if overall_ood > 0.1:
            recommendations.append("Design scale exceeds historical training range. Expect higher variance in runtime and area predictions.")
        if predictions.get("target_wns_ns") and predictions["target_wns_ns"].predicted_value < 0.0:
            recommendations.append(f"Predicted timing violation (WNS = {predictions['target_wns_ns'].predicted_value:.2f}ns). Consider relaxing clock period or floorplan utilization.")

        return ComprehensivePrediction(
            design_name=design_name,
            synthesis_runtime_s=predictions.get("target_synthesis_runtime_s"),
            placement_runtime_s=predictions.get("target_placement_runtime_s"),
            total_runtime_s=predictions.get("target_total_runtime_s"),
            cell_area_um2=predictions.get("target_cell_area_um2"),
            timing_wns_ns=predictions.get("target_wns_ns"),
            overall_ood_score=round(overall_ood, 3),
            recommendations=recommendations
        )
