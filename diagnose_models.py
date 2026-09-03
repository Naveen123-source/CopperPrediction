import pandas as pd
import numpy as np
from data_manager import DataManager
from metrics import calculate_all_metrics
from models import MODEL_REGISTRY

def diagnose():
    dm = DataManager("market_data.csv")
    h_data = dm.get_dataset_for_horizon(7)
    X, y = h_data["X"], h_data["y"]
    base = h_data["base_prices"]
    dates = h_data["dates"]

    splits = dm.split_chronological(X, y, horizon=7, train_ratio=0.80, val_ratio=0.10, dates=dates, base_prices=base)
    X_tr, y_tr = splits["X_train"], splits["y_train"]
    X_te, y_te = splits["X_test"], splits["y_test"]
    base_tr, base_te = splits["base_train"], splits["base_test"]

    print("==========================================================================")
    print("DATASET & SPLIT REGIME ANALYSIS:")
    print("==========================================================================")
    print(f"Total Rows: {len(X)}")
    print(f"Train Period: {splits['dates_train'].min()} to {splits['dates_train'].max()} | Target Range: [${y_tr.min():.2f} - ${y_tr.max():.2f}] | Mean: ${y_tr.mean():.2f}")
    print(f"Test  Period: {splits['dates_test'].min()} to {splits['dates_test'].max()} | Target Range: [${y_te.min():.2f} - ${y_te.max():.2f}] | Mean: ${y_te.mean():.2f}")
    print(f"Latest Origin Price at t: ${base_te.iloc[-1]:.4f} | Actual Horizon Target at t+7: ${y_te.iloc[-1]:.4f}")

    print("\n==========================================================================")
    print("EXPERIMENT A: Current Approach (Predicting Non-Stationary Raw Price Level)")
    print("==========================================================================")
    for name, cls in MODEL_REGISTRY.items():
        try:
            m = cls(horizon=7)
            m.fit(X_tr, y_tr)
            preds = m.predict(X_te)
            metrics = calculate_all_metrics(y_te, preds, base_te)
            print(f"{name:20s} -> Predicted Last: ${preds[-1]:.4f} | MAE: {metrics['MAE']:.4f} | RMSE: {metrics['RMSE']:.4f} | MAPE: {metrics['MAPE']:.2f}% | R2: {metrics['R²']:.4f}")
        except Exception as e:
            print(f"{name:20s} -> Error: {e}")

    print("\n==========================================================================")
    print("EXPERIMENT B: Stationary Approach (Predicting Direct Horizon Price Change Delta = y[t+h] - y[t])")
    print("==========================================================================")
    delta_tr = y_tr - base_tr
    for name, cls in MODEL_REGISTRY.items():
        try:
            m = cls(horizon=7)
            m.fit(X_tr, delta_tr)
            delta_preds = m.predict(X_te)
            final_preds = base_te.values + delta_preds
            metrics = calculate_all_metrics(y_te.values, final_preds, base_te.values)
            print(f"{name:20s} -> Predicted Last: ${final_preds[-1]:.4f} | MAE: {metrics['MAE']:.4f} | RMSE: {metrics['RMSE']:.4f} | MAPE: {metrics['MAPE']:.2f}% | R2: {metrics['R²']:.4f}")
        except Exception as e:
            print(f"{name:20s} -> Error: {e}")

if __name__ == "__main__":
    diagnose()
