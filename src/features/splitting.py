"""Design-level grouped dataset splitting strategy with zero data leakage guarantees."""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from src.common.logger import logger


class DatasetSplitter:
    """Partitions experiment datasets by unique RTL design family to prevent cross-split leakage."""

    def __init__(
        self,
        group_column: str = "design_name",
        train_ratio: float = 0.60,
        val_ratio: float = 0.20,
        test_ratio: float = 0.20,
        random_state: int = 42
    ):
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-4, "Ratios must sum to 1.0"
        self.group_column = group_column
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_state = random_state

    def split(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """Split DataFrame into Train, Validation, and Test partitions strictly grouped by design."""
        if self.group_column not in df.columns:
            raise KeyError(f"Group column '{self.group_column}' not found in DataFrame")

        unique_designs = np.array(sorted(df[self.group_column].unique()))
        num_designs = len(unique_designs)

        if num_designs < 3:
            raise ValueError(f"Need at least 3 unique designs for 3-way split; found {num_designs}: {unique_designs}")

        # Deterministic shuffle of unique design names
        rng = np.random.RandomState(self.random_state)
        shuffled_designs = rng.permutation(unique_designs)

        n_test = max(1, int(round(num_designs * self.test_ratio)))
        n_val = max(1, int(round(num_designs * self.val_ratio)))
        n_train = num_designs - n_test - n_val

        # Ensure train gets at least 1 design
        if n_train < 1:
            n_train = 1
            if n_val > 1:
                n_val -= 1
            elif n_test > 1:
                n_test -= 1

        train_designs = set(shuffled_designs[:n_train])
        val_designs = set(shuffled_designs[n_train:n_train + n_val])
        test_designs = set(shuffled_designs[n_train + n_val:])

        # Strict assertion against leakage
        assert len(train_designs.intersection(val_designs)) == 0, "Leakage detected between train and val"
        assert len(train_designs.intersection(test_designs)) == 0, "Leakage detected between train and test"
        assert len(val_designs.intersection(test_designs)) == 0, "Leakage detected between val and test"

        train_df = df[df[self.group_column].isin(train_designs)].copy()
        val_df = df[df[self.group_column].isin(val_designs)].copy()
        test_df = df[df[self.group_column].isin(test_designs)].copy()

        summary = {
            "total_samples": len(df),
            "total_designs": num_designs,
            "train_samples": len(train_df),
            "train_designs": sorted(list(train_designs)),
            "val_samples": len(val_df),
            "val_designs": sorted(list(val_designs)),
            "test_samples": len(test_df),
            "test_designs": sorted(list(test_designs)),
            "train_sample_pct": round(len(train_df) / len(df) * 100, 1),
            "val_sample_pct": round(len(val_df) / len(df) * 100, 1),
            "test_sample_pct": round(len(test_df) / len(df) * 100, 1),
        }

        logger.info(f"Group split complete: Train={summary['train_designs']}, Val={summary['val_designs']}, Test={summary['test_designs']}")
        return train_df, val_df, test_df, summary

    def save_splits(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        output_dir: Path
    ) -> Dict[str, Path]:
        """Save partitioned sets to disk in CSV and Parquet formats."""
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {}

        for name, data in [("train", train_df), ("val", val_df), ("test", test_df)]:
            c_p = output_dir / f"{name}.csv"
            p_p = output_dir / f"{name}.parquet"
            data.to_csv(c_p, index=False)
            data.to_parquet(p_p, index=False)
            paths[f"{name}_csv"] = c_p
            paths[f"{name}_parquet"] = p_p

        return paths
