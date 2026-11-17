"""Model artifact persistence, registry, and metadata tracking."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import joblib
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ModelMetadata(BaseModel):
    """Metadata schema for persisted EDA predictive models."""
    model_name: str
    target_name: str
    version: str = "v1"
    feature_names: List[str]
    training_metrics: Dict[str, float] = Field(default_factory=dict)
    cv_metrics: Dict[str, float] = Field(default_factory=dict)
    test_metrics: Dict[str, float] = Field(default_factory=dict)
    feature_bounds: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    trained_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    train_designs: List[str] = Field(default_factory=list)
    test_designs: List[str] = Field(default_factory=list)
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)


class ModelRegistry:
    """Manages saving, versioning, and loading trained ML model artifacts."""

    def __init__(self, base_dir: Path = Path("artifacts/models")):
        self.base_dir = base_dir

    def get_model_dir(self, version: str, target_name: str, model_name: str) -> Path:
        p = self.base_dir / version / target_name / model_name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def save_model(
        self,
        model: Any,
        metadata: ModelMetadata,
        scaler: Optional[Any] = None
    ) -> Path:
        """Persist model object, scaler, and JSON metadata to disk."""
        model_dir = self.get_model_dir(metadata.version, metadata.target_name, metadata.model_name)
        
        # Save model
        model_path = model_dir / "model.joblib"
        joblib.dump(model, model_path)

        # Save scaler if provided
        if scaler is not None:
            scaler_path = model_dir / "scaler.joblib"
            joblib.dump(scaler, scaler_path)

        # Save metadata
        meta_path = model_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        return model_dir

    def load_model(
        self,
        version: str,
        target_name: str,
        model_name: str
    ) -> tuple[Any, ModelMetadata, Optional[Any]]:
        """Load persisted model, metadata, and scaler."""
        model_dir = self.base_dir / version / target_name / model_name
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")

        model_path = model_dir / "model.joblib"
        meta_path = model_dir / "metadata.json"
        scaler_path = model_dir / "scaler.joblib"

        model = joblib.load(model_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = ModelMetadata(**json.load(f))

        scaler = joblib.load(scaler_path) if scaler_path.exists() else None
        return model, metadata, scaler
