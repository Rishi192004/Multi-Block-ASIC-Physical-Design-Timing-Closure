"""Model evaluation metrics with robust handling of near-zero and zero targets."""

from typing import Dict, Any, Union
import numpy as np
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


def compute_mape(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    epsilon: float = 1e-3
) -> float:
    """Calculate Mean Absolute Percentage Error (MAPE) with zero-target protection.

    For semiconductor metrics near zero (e.g. 0.0s runtime or 0.0ns slack),
    the denominator is clamped to max(|y_true|, epsilon) to avoid division by zero.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    denom = np.maximum(np.abs(y_t), epsilon)
    pct_errors = np.abs(y_t - y_p) / denom
    return float(np.mean(pct_errors) * 100.0)


def evaluate_predictions(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
    epsilon: float = 1e-3
) -> Dict[str, float]:
    """Compute comprehensive regression evaluation metrics: R2, MAE, RMSE, MAPE, MaxErr, Bias."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    if len(y_t) == 0:
        return {"r2": 0.0, "mae": 0.0, "rmse": 0.0, "mape": 0.0, "max_error": 0.0, "bias": 0.0}

    # Safeguard R2 if variance is zero
    if np.all(y_t == y_t[0]):
        r2 = 1.0 if np.allclose(y_t, y_p) else 0.0
    else:
        r2 = float(r2_score(y_t, y_p))

    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
    mape = compute_mape(y_t, y_p, epsilon=epsilon)
    max_err = float(np.max(np.abs(y_t - y_p)))
    bias = float(np.mean(y_p - y_t))  # positive = over-predicting

    return {
        "r2": round(r2, 4),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2),
        "max_error": round(max_err, 4),
        "bias": round(bias, 4),
    }
