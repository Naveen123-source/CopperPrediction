"""
Data Manager and Causal Feature Engineering Pipeline
Enforces strict chronological sorting and zero data leakage.
Constructs 11 mandatory causal features and direct multi-horizon targets.
"""

import os
import numpy as np
import pandas as pd

FORECAST_HORIZONS = [1, 7, 15, 30, 60, 90]
FIXED_HORIZONS = [1, 7, 15, 30, 60, 90]

CONTINUOUS_RANGES = {
    "1-7": list(range(1, 8)),
    "1-15": list(range(1, 16)),
    "1-30": list(range(1, 31)),
    "1-60": list(range(1, 61)),
    "1-90": list(range(1, 91))
}

RATIOS_CONFIG = {
    "60-40": 0.60,
    "70-30": 0.70,
    "75-25": 0.75,
    "80-20": 0.80,
    "85-15": 0.85
}

def get_working_day_target_date(start_date, horizon_days: int) -> str:
    """
    Computes the forecast target date by stepping forward exactly `horizon_days` working days
    (Monday through Friday), strictly skipping Saturdays and Sundays.
    """
    current = pd.to_datetime(start_date)
    working_days_count = 0
    while working_days_count < horizon_days:
        current += pd.Timedelta(days=1)
        if current.weekday() < 5:  # 0=Monday, ..., 4=Friday (excludes Saturday 5 and Sunday 6)
            working_days_count += 1
    return current.strftime("%Y-%m-%d")


FEATURE_COLUMNS = [
    "Copper Price Lag 1 Return",
    "Copper Price Lag 3 Return",
    "Copper Price Lag 10 Return",
    "Copper Rolling Mean Relative",
    "Copper Momentum Return",
    "Crude Oil (WTI) Return",
    "3M vs Cash Basis Spread",
    "LME Stocks Change",
    "US Dollar Index (DXY) Return",
    "Interest Rate Change",
    "Realized Volatility"
]

class DataManager:
    def __init__(self, data_path="market_data.csv"):
        self.data_path = data_path
        self.raw_df = None
        self.processed_df = None
        self.load_and_process()
        
    def load_and_process(self):
        """Loads data, sorts chronologically, validates columns, and builds causal features."""
        if not os.path.exists(self.data_path):
            from data_generator import generate_market_dataset
            self.raw_df = generate_market_dataset(self.data_path)
        else:
            self.raw_df = pd.read_csv(self.data_path)
            
        # Ensure Date column is parsed and sorted strictly chronologically
        if "Date" in self.raw_df.columns:
            self.raw_df["Date"] = pd.to_datetime(self.raw_df["Date"])
            self.raw_df = self.raw_df.sort_values("Date").reset_index(drop=True)
            
        # Map column names if needed
        col_map = {
            "Open": "Copper_Open",
            "High": "Copper_High",
            "Low": "Copper_Low",
            "Close": "Copper_Close",
            "Volume": "Copper_Volume"
        }
        for k, v in col_map.items():
            if k in self.raw_df.columns and v not in self.raw_df.columns:
                self.raw_df[v] = self.raw_df[k]
                
        # Fill standard fallbacks if any macroeconomic column is missing
        if "Copper_Close" not in self.raw_df.columns:
            raise ValueError("Dataset must contain 'Copper_Close' or 'Close' column.")
            
        close = self.raw_df["Copper_Close"]
        
        if "Crude_Oil" not in self.raw_df.columns:
            self.raw_df["Crude_Oil"] = 70.0 + np.cumsum(np.random.normal(0, 0.5, len(close)))
        if "DXY_Index" not in self.raw_df.columns:
            self.raw_df["DXY_Index"] = 100.0 + np.cumsum(np.random.normal(0, 0.2, len(close)))
        if "Interest_Rate" not in self.raw_df.columns:
            self.raw_df["Interest_Rate"] = 3.5 + np.cumsum(np.random.normal(0, 0.02, len(close)))
        if "LME_Stocks" not in self.raw_df.columns:
            self.raw_df["LME_Stocks"] = 150000 + np.cumsum(np.random.normal(0, 500, len(close)))
        if "Basis_Spread_3M_Cash" not in self.raw_df.columns:
            self.raw_df["Basis_Spread_3M_Cash"] = (close - 3.5) * 15.0
            
        df = self.raw_df.copy()
        
        # -------------------------------------------------------------
        # STRICT CAUSAL STATIONARY & RELATIVE FEATURE ENGINEERING
        # All features constructed using only observations available up to origin time t
        # -------------------------------------------------------------
        
        # 1. Copper Price Lag 1 Return (Relative 1-day return)
        df["Copper Price Lag 1 Return"] = (close.shift(1) - close.shift(2)) / (close.shift(2) + 1e-8)
        
        # 2. Copper Price Lag 3 Return (Relative 3-day return)
        df["Copper Price Lag 3 Return"] = (close.shift(1) - close.shift(3)) / (close.shift(3) + 1e-8)
        
        # 3. Copper Price Lag 10 Return (Relative 10-day return)
        df["Copper Price Lag 10 Return"] = (close.shift(1) - close.shift(10)) / (close.shift(10) + 1e-8)
        
        # 4. Copper Rolling Mean Relative (10-day causal rolling mean relative to previous close)
        df["Copper Rolling Mean Relative"] = (close.shift(1).rolling(window=10).mean() - close.shift(1)) / (close.shift(1) + 1e-8)
        
        # 5. Copper Momentum Return (10-day momentum percentage return)
        df["Copper Momentum Return"] = (close.shift(1) - close.shift(10)) / (close.shift(10) + 1e-8)
        
        # 6. Crude Oil (WTI) Return
        df["Crude Oil (WTI) Return"] = df["Crude_Oil"].pct_change().shift(1)
        
        # 7. 3M vs Cash Basis Spread (Normalized by historical close)
        df["3M vs Cash Basis Spread"] = df["Basis_Spread_3M_Cash"].shift(1) / (close.shift(1) + 1e-8)
        
        # 8. LME Stocks Change (Relative percentage change)
        df["LME Stocks Change"] = df["LME_Stocks"].pct_change().shift(1)
        
        # 9. US Dollar Index (DXY) Return
        df["US Dollar Index (DXY) Return"] = df["DXY_Index"].pct_change().shift(1)
        
        # 10. Interest Rate Change
        df["Interest Rate Change"] = df["Interest_Rate"].diff().shift(1)
        
        # 11. Realized Volatility (10-day rolling std of causal price returns)
        df["Realized Volatility"] = close.pct_change().shift(1).rolling(window=10).std()
        
        # -------------------------------------------------------------
        # DIRECT MULTI-HORIZON TARGETS:
        # Target_Delta_h = Copper_Close[t + h] - Copper_Close[t] (Model training target)
        # Target_hD      = Copper_Close[t + h]                 (Ground truth evaluation target)
        # -------------------------------------------------------------
        targets_dict = {}
        for h in range(1, 91):
            targets_dict[f"Target_Delta_{h}D"] = close.shift(-h) - close
            targets_dict[f"Target_{h}D"] = close.shift(-h)
            
        targets_df = pd.DataFrame(targets_dict, index=df.index)
        df = pd.concat([df, targets_df], axis=1)
            
        # Drop rows where lag features are NaN (warmup period, first 10-15 rows)
        # Keep rows where target is NaN only for future forecasting purposes
        valid_feature_mask = ~df[FEATURE_COLUMNS].isna().any(axis=1)
        self.processed_df = df[valid_feature_mask].reset_index(drop=True)
        return self.processed_df
        
    def get_market_summary(self):
        """Returns the latest market summary snapshot for dashboard cards."""
        if self.raw_df is None or len(self.raw_df) == 0:
            return {}
            
        latest = self.raw_df.iloc[-1]
        prev = self.raw_df.iloc[-2] if len(self.raw_df) > 1 else latest
        
        close = float(latest.get("Copper_Close", 0.0))
        prev_close = float(prev.get("Copper_Close", close))
        change = round(close - prev_close, 4)
        pct_change = round((change / (prev_close + 1e-8)) * 100, 2)
        
        return {
            "date": str(latest.get("Date", "")),
            "copper_open": float(latest.get("Copper_Open", close)),
            "copper_high": float(latest.get("Copper_High", close)),
            "copper_low": float(latest.get("Copper_Low", close)),
            "copper_close": close,
            "copper_change": change,
            "copper_pct_change": pct_change,
            "copper_volume": int(latest.get("Copper_Volume", 0)),
            "copper_stock": int(latest.get("LME_Stocks", 0)),
            "lme_stocks": int(latest.get("LME_Stocks", 0)),
            "crude_oil": float(latest.get("Crude_Oil", 0.0)),
            "dxy_index": float(latest.get("DXY_Index", 0.0)),
            "interest_rate": float(latest.get("Interest_Rate", 0.0)),
            "basis_spread": float(latest.get("Basis_Spread_3M_Cash", 0.0))
        }

    def get_dataset_for_horizon(self, horizon):
        """
        Extracts feature matrix X and delta target y for direct horizon h.
        Target Delta: Target_Delta_h = Copper_Close[t + h] - Copper_Close[t]
        Excludes unobserved future tail rows from training.
        """
        target_delta_col = f"Target_Delta_{horizon}D"
        target_actual_col = f"Target_{horizon}D"
        if target_delta_col not in self.processed_df.columns:
            raise ValueError(f"Target column {target_delta_col} not found.")
            
        # Supervised dataset: rows where both features AND target are known
        valid_mask = ~self.processed_df[target_delta_col].isna()
        supervised_df = self.processed_df[valid_mask].copy()
        
        X = supervised_df[FEATURE_COLUMNS].copy()
        y_delta = supervised_df[target_delta_col].copy()      # Model training target (Delta_h)
        y_actual = supervised_df[target_actual_col].copy()   # Ground truth actual future price
        dates = supervised_df["Date"].copy()
        base_prices = supervised_df["Copper_Close"].copy()    # Price at origin t
        
        # Latest row available at forecast origin (for true future forecast)
        latest_row = self.processed_df.iloc[-1]
        X_latest = pd.DataFrame([latest_row[FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        latest_date = latest_row["Date"]
        latest_base_price = float(latest_row["Copper_Close"])
        
        return {
            "X": X,
            "y": y_delta,
            "y_actual": y_actual,
            "dates": dates,
            "base_prices": base_prices,
            "X_latest": X_latest,
            "latest_date": latest_date,
            "latest_base_price": latest_base_price,
            "full_df": supervised_df
        }

    def split_chronological(self, X, y, horizon=1, train_ratio=0.80, val_ratio=0.10, dates=None, base_prices=None):
        """
        Strict horizon-aware purged chronological train / validation / test split.
        Purges the final (horizon) samples from training and validation partitions to guarantee
        that training and validation target realization dates NEVER spill over into the subsequent partition.
        Zero data leakage guaranteed.
        """
        n = len(X)
        purge_gap = max(0, horizon)
        
        if val_ratio is None or val_ratio <= 0:
            train_size = int(n * train_ratio)
            train_end = max(1, train_size - purge_gap)
            train_idx = slice(0, train_end)
            test_idx = slice(train_size, n)
            val_idx = None
            
            splits = {
                "X_train": X.iloc[train_idx].copy(),
                "y_train": y.iloc[train_idx].copy(),
                "X_val": None,
                "y_val": None,
                "X_test": X.iloc[test_idx].copy(),
                "y_test": y.iloc[test_idx].copy(),
                "dates_train": dates.iloc[train_idx].copy() if dates is not None else None,
                "dates_val": None,
                "dates_test": dates.iloc[test_idx].copy() if dates is not None else None,
                "base_train": base_prices.iloc[train_idx].copy() if base_prices is not None else None,
                "base_val": None,
                "base_test": base_prices.iloc[test_idx].copy() if base_prices is not None else None
            }
        else:
            # 3-way chronological split: train_ratio -> (1 - train_ratio) split into val and test
            train_size = int(n * train_ratio)
            remaining = n - train_size
            val_size = int(remaining * 0.5)
            test_size = remaining - val_size
            
            val_start = train_size
            test_start = train_size + val_size
            
            train_end = max(1, train_size - purge_gap)
            val_end = max(val_start + 1, test_start - purge_gap)
            
            train_idx = slice(0, train_end)
            val_idx = slice(val_start, val_end)
            test_idx = slice(test_start, n)
            
            splits = {
                "X_train": X.iloc[train_idx].copy(),
                "y_train": y.iloc[train_idx].copy(),
                "X_val": X.iloc[val_idx].copy(),
                "y_val": y.iloc[val_idx].copy(),
                "X_test": X.iloc[test_idx].copy(),
                "y_test": y.iloc[test_idx].copy(),
                "dates_train": dates.iloc[train_idx].copy() if dates is not None else None,
                "dates_val": dates.iloc[val_idx].copy() if dates is not None else None,
                "dates_test": dates.iloc[test_idx].copy() if dates is not None else None,
                "base_train": base_prices.iloc[train_idx].copy() if base_prices is not None else None,
                "base_val": base_prices.iloc[val_idx].copy() if base_prices is not None else None,
                "base_test": base_prices.iloc[test_idx].copy() if base_prices is not None else None
            }
        return splits
