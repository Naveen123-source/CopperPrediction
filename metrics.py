"""
Evaluation Metrics Engine
Implements all 11 evaluation metrics required for multi-horizon forecasting:
1. MAE (Mean Absolute Error)
2. RMSE (Root Mean Squared Error)
3. MAPE (Mean Absolute Percentage Error)
4. sMAPE (Symmetric Mean Absolute Percentage Error)
5. R² (Coefficient of Determination)
6. Mean Error (Bias)
7. Directional Accuracy
8. UP Accuracy
9. DOWN Accuracy
10. Max Absolute Error
11. Error Standard Deviation
"""

import numpy as np

def calculate_mae(y_true, y_pred):
    """Mean Absolute Error"""
    return float(np.mean(np.abs(y_true - y_pred)))

def calculate_rmse(y_true, y_pred):
    """Root Mean Squared Error"""
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def calculate_mape(y_true, y_pred):
    """Mean Absolute Percentage Error (%)"""
    epsilon = 1e-8
    return float(np.mean(np.abs((y_true - y_pred) / (y_true + epsilon))) * 100.0)

def calculate_smape(y_true, y_pred):
    """Symmetric Mean Absolute Percentage Error (%)"""
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0 + 1e-8
    return float(np.mean(np.abs(y_pred - y_true) / denominator) * 100.0)

def calculate_r2(y_true, y_pred):
    """R-squared (Coefficient of Determination)"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    r2 = 1.0 - (ss_res / ss_tot)
    return float(r2)

def calculate_mean_error(y_true, y_pred):
    """Mean Error (Prediction Bias: y_pred - y_true)"""
    return float(np.mean(y_pred - y_true))

def calculate_directional_accuracy(y_true, y_pred, y_base=None):
    """
    Directional Accuracy (%):
    If y_base (price at origin t) is provided:
        sign(y_pred - y_base) == sign(y_true - y_base)
    Otherwise:
        sign(diff(y_pred)) == sign(diff(y_true))
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    
    if len(y_true) == 0:
        return 0.0
        
    if y_base is not None:
        y_base = np.asarray(y_base)
        actual_dir = np.sign(y_true - y_base)
        pred_dir = np.sign(y_pred - y_base)
        correct = (actual_dir == pred_dir)
        return float(np.mean(correct) * 100.0)
    else:
        if len(y_true) < 2:
            return 100.0 if np.allclose(y_true, y_pred) else 0.0
        actual_diff = np.diff(y_true)
        pred_diff = np.diff(y_pred)
        correct = (np.sign(actual_diff) == np.sign(pred_diff))
        return float(np.mean(correct) * 100.0)

def calculate_up_accuracy(y_true, y_pred, y_base=None):
    """UP Accuracy (%): Accuracy strictly when actual market moved UP."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    
    if y_base is not None:
        y_base = np.asarray(y_base)
        actual_change = y_true - y_base
        pred_change = y_pred - y_base
    else:
        if len(y_true) < 2:
            return 0.0
        actual_change = np.diff(y_true)
        pred_change = np.diff(y_pred)
        
    up_mask = actual_change > 0
    if not np.any(up_mask):
        return 100.0  # No UP instances to misclassify
    correct_up = (np.sign(pred_change[up_mask]) == np.sign(actual_change[up_mask]))
    return float(np.mean(correct_up) * 100.0)

def calculate_down_accuracy(y_true, y_pred, y_base=None):
    """DOWN Accuracy (%): Accuracy strictly when actual market moved DOWN."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    
    if y_base is not None:
        y_base = np.asarray(y_base)
        actual_change = y_true - y_base
        pred_change = y_pred - y_base
    else:
        if len(y_true) < 2:
            return 0.0
        actual_change = np.diff(y_true)
        pred_change = np.diff(y_pred)
        
    down_mask = actual_change < 0
    if not np.any(down_mask):
        return 100.0  # No DOWN instances to misclassify
    correct_down = (np.sign(pred_change[down_mask]) == np.sign(actual_change[down_mask]))
    return float(np.mean(correct_down) * 100.0)

def calculate_max_abs_error(y_true, y_pred):
    """Max Absolute Error"""
    return float(np.max(np.abs(y_true - y_pred)))

def calculate_error_std(y_true, y_pred):
    """Error Standard Deviation"""
    errors = y_true - y_pred
    return float(np.std(errors))

ALL_METRICS = [
    "MAE",
    "RMSE",
    "MAPE",
    "sMAPE",
    "R²",
    "Mean Error (Bias)",
    "Directional Accuracy",
    "UP Accuracy",
    "DOWN Accuracy",
    "Max Absolute Error",
    "Error Std Dev"
]

METRIC_OPTIMIZATION_DIRECTION = {
    "MAE": "minimize",
    "RMSE": "minimize",
    "MAPE": "minimize",
    "sMAPE": "minimize",
    "R²": "maximize",
    "Mean Error (Bias)": "minimize_abs",
    "Directional Accuracy": "maximize",
    "UP Accuracy": "maximize",
    "DOWN Accuracy": "maximize",
    "Max Absolute Error": "minimize",
    "Error Std Dev": "minimize"
}

def calculate_all_metrics(y_true, y_pred, y_base=None):
    """
    Computes all 11 metrics cleanly and returns a structured dictionary.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    
    # Handle NaN or Inf gracefully
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred) & ~np.isinf(y_true) & ~np.isinf(y_pred)
    if y_base is not None:
        y_base = np.asarray(y_base, dtype=float)
        mask = mask & ~np.isnan(y_base)
        y_base_clean = y_base[mask]
    else:
        y_base_clean = None
        
    y_t = y_true[mask]
    y_p = y_pred[mask]
    
    if len(y_t) == 0:
        return {m: 0.0 for m in ALL_METRICS}
        
    return {
        "MAE": round(calculate_mae(y_t, y_p), 4),
        "RMSE": round(calculate_rmse(y_t, y_p), 4),
        "MAPE": round(calculate_mape(y_t, y_p), 2),
        "sMAPE": round(calculate_smape(y_t, y_p), 2),
        "R²": round(calculate_r2(y_t, y_p), 4),
        "Mean Error (Bias)": round(calculate_mean_error(y_t, y_p), 4),
        "Directional Accuracy": round(calculate_directional_accuracy(y_t, y_p, y_base_clean), 2),
        "UP Accuracy": round(calculate_up_accuracy(y_t, y_p, y_base_clean), 2),
        "DOWN Accuracy": round(calculate_down_accuracy(y_t, y_p, y_base_clean), 2),
        "Max Absolute Error": round(calculate_max_abs_error(y_t, y_p), 4),
        "Error Std Dev": round(calculate_error_std(y_t, y_p), 4)
    }

def get_single_metric(y_true, y_pred, metric_name, y_base=None):
    """Computes a single specific metric."""
    metrics = calculate_all_metrics(y_true, y_pred, y_base)
    return metrics.get(metric_name, 0.0)
