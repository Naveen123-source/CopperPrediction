"""
Time-Series Aware Metric-Specific Hyperparameter Tuner
Zero Data Leakage: Uses ONLY training data with internal TimeSeriesSplit cross-validation.
Tunes parameters specifically targeting the user-selected error metric.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from metrics import calculate_all_metrics, get_single_metric, METRIC_OPTIMIZATION_DIRECTION
from models import MODEL_REGISTRY

# Parameter search grids per model type
PARAM_GRIDS = {
    "XGBoost": [
        {"n_estimators": 50, "max_depth": 3, "learning_rate": 0.03, "subsample": 0.8},
        {"n_estimators": 80, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8},
        {"n_estimators": 120, "max_depth": 5, "learning_rate": 0.08, "subsample": 0.9},
        {"n_estimators": 150, "max_depth": 6, "learning_rate": 0.05, "subsample": 0.85},
    ],
    "CatBoost": [
        {"iterations": 80, "depth": 3, "learning_rate": 0.03, "l2_leaf_reg": 2.0},
        {"iterations": 120, "depth": 4, "learning_rate": 0.05, "l2_leaf_reg": 3.0},
        {"iterations": 150, "depth": 5, "learning_rate": 0.08, "l2_leaf_reg": 4.0},
        {"iterations": 200, "depth": 6, "learning_rate": 0.05, "l2_leaf_reg": 3.0},
    ],
    "LightGBM": [
        {"n_estimators": 60, "max_depth": 3, "num_leaves": 15, "learning_rate": 0.03},
        {"n_estimators": 100, "max_depth": 4, "num_leaves": 25, "learning_rate": 0.05},
        {"n_estimators": 120, "max_depth": 5, "num_leaves": 31, "learning_rate": 0.08},
        {"n_estimators": 150, "max_depth": 6, "num_leaves": 45, "learning_rate": 0.05},
    ],
    "RandomForest": [
        {"n_estimators": 50, "max_depth": 5, "min_samples_split": 4},
        {"n_estimators": 80, "max_depth": 7, "min_samples_split": 3},
        {"n_estimators": 100, "max_depth": 9, "min_samples_split": 2},
        {"n_estimators": 120, "max_depth": 11, "min_samples_split": 2},
    ],
    "Stage Regression": [
        {"stage1_alpha": 0.1, "stage2_n_estimators": 60, "stage2_max_depth": 3, "stage2_learning_rate": 0.03},
        {"stage1_alpha": 1.0, "stage2_n_estimators": 80, "stage2_max_depth": 4, "stage2_learning_rate": 0.05},
        {"stage1_alpha": 5.0, "stage2_n_estimators": 100, "stage2_max_depth": 5, "stage2_learning_rate": 0.08},
    ],
    "Stacking Ensemble": [
        {"n_splits": 3, "meta_alpha": 0.1},
        {"n_splits": 3, "meta_alpha": 1.0},
        {"n_splits": 4, "meta_alpha": 5.0},
    ],
    "ARIMA": [
        {"order": (1, 1, 0), "trend": "c"},
        {"order": (2, 1, 1), "trend": "c"},
        {"order": (1, 1, 1), "trend": "n"},
    ],
    "SARIMAX": [
        {"order": (1, 1, 0), "maxiter": 30},
        {"order": (1, 1, 1), "maxiter": 50},
        {"order": (2, 1, 1), "maxiter": 50},
    ],
    "LSTM": [
        {"window_size": 8, "lstm_units": 24, "epochs": 15, "learning_rate": 0.005},
        {"window_size": 10, "lstm_units": 32, "epochs": 20, "learning_rate": 0.005},
        {"window_size": 15, "lstm_units": 48, "epochs": 20, "learning_rate": 0.003},
    ]
}

class MetricSpecificTuner:
    def __init__(self, n_splits=3):
        self.n_splits = n_splits

    def tune(self, model_name, horizon, target_metric, X_train, y_train, base_train=None):
        """
        Executes internal TimeSeriesSplit cross-validation strictly on training data
        to find hyperparameters that optimize target_metric.
        """
        model_cls = MODEL_REGISTRY.get(model_name)
        if model_cls is None:
            raise ValueError(f"Unknown model: {model_name}")

        grid = PARAM_GRIDS.get(model_name, [{}])
        if len(grid) <= 1:
            return grid[0] if grid else {}

        n_samples = len(X_train)
        tscv_splits = min(self.n_splits, max(2, n_samples // 120))
        tscv = TimeSeriesSplit(n_splits=tscv_splits)

        direction = METRIC_OPTIMIZATION_DIRECTION.get(target_metric, "minimize")
        best_score = float("inf") if direction in ["minimize", "minimize_abs"] else float("-inf")
        best_params = grid[0]

        X_mat = np.asarray(X_train)
        y_mat = np.asarray(y_train)
        base_mat = np.asarray(base_train) if base_train is not None else None

        purge_gap = max(0, horizon)
        for param_candidate in grid:
            fold_scores = []
            try:
                for fold_train_idx, fold_val_idx in tscv.split(X_mat):
                    # Purge fold training boundary by horizon to eliminate target overlap into validation fold
                    if len(fold_train_idx) > purge_gap + 20:
                        purged_train_idx = fold_train_idx[:-purge_gap]
                    else:
                        purged_train_idx = fold_train_idx[:max(1, len(fold_train_idx) // 2)]

                    f_X_tr, f_y_tr = X_mat[purged_train_idx], y_mat[purged_train_idx]
                    f_X_val, f_y_val = X_mat[fold_val_idx], y_mat[fold_val_idx]
                    f_base_val = base_mat[fold_val_idx] if base_mat is not None else None

                    inst = model_cls(horizon=horizon, params=param_candidate)
                    inst.fit(f_X_tr, f_y_tr)
                    f_pred_deltas = inst.predict(f_X_val)

                    # Compute score on reconstructed prices
                    if f_base_val is not None:
                        f_pred_prices = f_base_val + f_pred_deltas
                        f_actual_prices = f_base_val + f_y_val
                        score = get_single_metric(f_actual_prices, f_pred_prices, target_metric, y_base=f_base_val)
                    else:
                        score = get_single_metric(f_y_val, f_pred_deltas, target_metric, y_base=None)
                        
                    fold_scores.append(score)

                if len(fold_scores) > 0:
                    avg_score = float(np.mean(fold_scores))

                    if direction == "minimize":
                        if avg_score < best_score:
                            best_score = avg_score
                            best_params = param_candidate
                    elif direction == "minimize_abs":
                        if abs(avg_score) < abs(best_score):
                            best_score = avg_score
                            best_params = param_candidate
                    else:  # maximize
                        if avg_score > best_score:
                            best_score = avg_score
                            best_params = param_candidate
            except Exception as e:
                # If a specific param configuration fails, continue to next
                continue

        return best_params
