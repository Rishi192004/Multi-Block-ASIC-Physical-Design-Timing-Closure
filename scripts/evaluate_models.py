#!/usr/bin/env python3
"""Evaluation and inference driver for trained EDA predictive models."""

import sys
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.inference import EDAPredictor
from src.models.registry import ModelRegistry
from src.models.metrics import evaluate_predictions
from src.common.logger import logger


def main():
    parser = argparse.ArgumentParser(description="EDA-Genius Predictive Modeling Evaluator & Inference CLI")
    parser.add_argument("--version", type=str, default="v1", help="Model artifact version")
    parser.add_argument("--test-data", type=str, default="artifacts/datasets/v1/splits/test.parquet",
                        help="Path to evaluation dataset")
    parser.add_argument("--sample-inference", action="store_true",
                        help="Run end-to-end sample prediction with OOD analysis on first test row")

    args = parser.parse_args()

    print("=" * 75)
    print("  EDA-Genius: Predictive Model Evaluation & Inference Engine")
    print(f"  Model Version: {args.version}")
    print(f"  Evaluation Dataset: {args.test_data}")
    print("=" * 75)

    test_path = Path(args.test_data)
    if not test_path.exists():
        print(f"[ERROR] Evaluation dataset not found at {test_path}")
        sys.exit(1)

    df_test = pd.read_parquet(test_path) if test_path.suffix == ".parquet" else pd.read_csv(test_path)
    print(f"\nLoaded {len(df_test)} test evaluation samples across designs: {list(df_test['design_name'].unique())}")

    predictor = EDAPredictor(version=args.version)
    predictor.load_champion_models()

    if not predictor.models:
        print("[ERROR] No champion models found in registry. Run scripts/train_models.py first.")
        sys.exit(1)

    print("\n" + "=" * 75)
    print("  Evaluation Results on Held-Out Test Partition (Zero Data Leakage)")
    print("=" * 75)
    print(f"{'Target Outcome':<32} | {'Champion Model':<20} | {'Test R²':<8} | {'Test MAE':<10} | {'Test MAPE':<10}")
    print("-" * 90)

    for target_name, model in predictor.models.items():
        meta = predictor.metadata[target_name]
        expected_cols = meta.feature_names

        X = df_test[[c for c in expected_cols if c in df_test.columns]].copy().fillna(0.0)
        # Pad any missing columns with 0
        for c in expected_cols:
            if c not in X.columns:
                X[c] = 0.0
        X = X[expected_cols]

        y_true = df_test[target_name].values
        y_pred = model.predict(X)

        metrics = evaluate_predictions(y_true, y_pred)
        clean_name = target_name.replace("target_", "")
        print(f"{clean_name:<32} | {meta.model_name:<20} | {metrics['r2']:<8.3f} | {metrics['mae']:<10.3f} | {metrics['mape']:<9.1f}%")

    if args.sample_inference:
        print("\n" + "=" * 75)
        print("  Sample Inference Simulation with Out-of-Distribution (OOD) Guard")
        print("=" * 75)
        sample_row = df_test.iloc[0].to_dict()
        design_name = sample_row.get("design_name", "sample_test_design")

        comp_pred = predictor.predict_from_features(sample_row, design_name=design_name)
        print(f"\nTarget Design: [{comp_pred.design_name}]")
        print(f"Overall OOD Score: {comp_pred.overall_ood_score * 100:.1f}%")

        print("\nPredicted Outcomes:")
        for attr, pred in [
            ("Synthesis Runtime", comp_pred.synthesis_runtime_s),
            ("Placement Runtime", comp_pred.placement_runtime_s),
            ("Total Flow Runtime", comp_pred.total_runtime_s),
            ("Standard Cell Area", comp_pred.cell_area_um2),
            ("Worst Slack (WNS)", comp_pred.timing_wns_ns),
        ]:
            if pred:
                ood_flag = " [OOD WARNING]" if pred.is_out_of_distribution else ""
                print(f"  - {attr:<22}: {pred.predicted_value:.3f} {pred.unit} (Confidence: {pred.confidence_level}{ood_flag})")
                if pred.caveats:
                    print(f"    * Caveat: {pred.caveats}")

        if comp_pred.recommendations:
            print("\nOptimization Recommendations:")
            for rec in comp_pred.recommendations:
                print(f"  * {rec}")


if __name__ == "__main__":
    main()
