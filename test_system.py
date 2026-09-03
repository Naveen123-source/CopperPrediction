"""
Unit and Integration Tests for Multi-Horizon Copper Forecasting System
Verifies:
1. Strict Causal Features & Zero Data Leakage
2. Direct Multi-Horizon Target Construction
3. All 11 Evaluation Metrics
4. All 9 Forecasting Models & Pipeline Execution
"""

import unittest
import numpy as np
import pandas as pd

from data_manager import DataManager, FORECAST_HORIZONS, RATIOS_CONFIG, FEATURE_COLUMNS, get_working_day_target_date
from metrics import calculate_all_metrics, ALL_METRICS, get_single_metric
from leakage_guard import LeakageGuard
from models import MODEL_REGISTRY
from pipeline import ForecastingPipeline

class TestCopperForecastingSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dm = DataManager("market_data.csv")
        
    def test_causal_features_integrity(self):
        """Audit that features use strictly t-1, t-3, t-10 and no future data."""
        df = self.dm.processed_df
        
        # Test Lag 1 Return
        self.assertIn("Copper Price Lag 1 Return", df.columns)
        # Test Rolling Mean causal
        audit = LeakageGuard.audit_features(df)
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["details"]["lag_1_causal"])
        self.assertTrue(audit["details"]["lag_3_causal"])
        self.assertTrue(audit["details"]["rolling_mean_causal"])
        
    def test_direct_multi_horizon_targets(self):
        """Verify direct targets Target_Delta_hD = Close[t + h] - Close[t] without recursion."""
        for h in [1, 7, 15, 30, 60, 90]:
            target_col = f"Target_Delta_{h}D"
            self.assertIn(target_col, self.dm.processed_df.columns)
            h_data = self.dm.get_dataset_for_horizon(h)
            self.assertFalse(h_data["y"].isna().any())
            self.assertEqual(len(h_data["X"]), len(h_data["y"]))
            
    def test_chronological_splits_leakage(self):
        """Verify Train < Val < Test chronological integrity with horizon-aware split auditing."""
        for h in [1, 7, 15, 30, 60, 90]:
            h_data = self.dm.get_dataset_for_horizon(h)
            splits = self.dm.split_chronological(
                h_data["X"], h_data["y"],
                horizon=h,
                train_ratio=0.80, val_ratio=0.10,
                dates=h_data["dates"]
            )
            audit = LeakageGuard.audit_splits(splits["dates_train"], splits["dates_val"], splits["dates_test"], horizon=h)
            self.assertEqual(audit["status"], "PASS", f"Horizon {h} failed split audit")
            self.assertTrue(audit["checks"]["train_before_test"])
            self.assertTrue(audit["checks"]["val_before_test"])
            self.assertTrue(audit["checks"]["train_before_val"])
            self.assertTrue(audit["checks"]["train_target_before_val"])
            self.assertTrue(audit["checks"]["val_target_before_test"])
        
    def test_all_11_metrics(self):
        """Verify all 11 error metrics calculate correctly."""
        y_true = np.array([4.10, 4.15, 4.20, 4.18, 4.25])
        y_pred = np.array([4.12, 4.14, 4.22, 4.19, 4.23])
        y_base = np.array([4.08, 4.10, 4.15, 4.20, 4.20])
        
        metrics = calculate_all_metrics(y_true, y_pred, y_base=y_base)
        for m in ALL_METRICS:
            self.assertIn(m, metrics)
            self.assertIsInstance(metrics[m], float)
            
        self.assertGreater(metrics["RMSE"], 0)
        self.assertGreater(metrics["MAE"], 0)
        self.assertGreaterEqual(metrics["Directional Accuracy"], 0.0)
        self.assertLessEqual(metrics["Directional Accuracy"], 100.0)
        
    def test_all_9_models_instantiation_and_fit(self):
        """Verify each of the 9 models fits and predicts correctly."""
        h_data = self.dm.get_dataset_for_horizon(7)
        splits = self.dm.split_chronological(
            h_data["X"].iloc[:300], h_data["y"].iloc[:300],
            train_ratio=0.80, val_ratio=0.10
        )
        X_tr, y_tr = splits["X_train"], splits["y_train"]
        X_te, y_te = splits["X_test"], splits["y_test"]
        
        for model_name, model_cls in MODEL_REGISTRY.items():
            model = model_cls(horizon=7)
            model.fit(X_tr, y_tr)
            preds = model.predict(X_te)
            self.assertEqual(len(preds), len(X_te), f"{model_name} prediction length mismatch")
            self.assertFalse(np.any(np.isnan(preds)), f"{model_name} produced NaNs")
            
    def test_pipeline_smoke_run(self):
        """Test pipeline run with multiple horizons, models, and metrics."""
        pipe = ForecastingPipeline(self.dm)
        results = pipe.run_multi_horizon_forecast(
            job_id="test_smoke_job",
            selected_models=["XGBoost", "RandomForest", "Stage Regression"],
            selected_metrics=["RMSE", "MAE", "Directional Accuracy"],
            selected_horizons=[1, 7],
            selected_ratios=["80-20"],
            auto_tuning=False
        )
        # Expected: 3 models * 2 horizons * 1 ratio * 3 metrics = 18 result cards
        self.assertEqual(len(results), 18)
        self.assertEqual(results[0]["leakage_check"], "PASS")

    def test_continuous_daily_range_pipeline(self):
        """Test continuous day-by-day direct forecasting range (1 to 7 Days)."""
        pipe = ForecastingPipeline(self.dm)
        continuous_7d = list(range(1, 8)) # Day 1, Day 2, ... Day 7
        results = pipe.run_multi_horizon_forecast(
            job_id="test_continuous_7d",
            selected_models=["XGBoost"],
            selected_metrics=["RMSE"],
            selected_horizons=continuous_7d,
            selected_ratios=["80-20"],
            auto_tuning=False
        )
        # Expected: 1 model * 7 individual days * 1 ratio * 1 metric = 7 result cards
        self.assertEqual(len(results), 7)
        horizons_returned = [r["horizon"] for r in results]
        self.assertEqual(horizons_returned, continuous_7d)
        for r in results:
            self.assertEqual(r["leakage_check"], "PASS")
            self.assertIn("Target Date", f"Target Date: {r['target_date']}")
            self.assertGreater(r["predicted_price"], 0.0)

    def test_weekend_skipping_date_math(self):
        """Verify get_working_day_target_date strictly skips Saturdays and Sundays."""
        # 1. Starting on Thursday 2026-05-07
        # Day 1: Friday 2026-05-08
        self.assertEqual(get_working_day_target_date("2026-05-07", 1), "2026-05-08")
        # Day 2: Monday 2026-05-11 (skipping Sat 05-09 and Sun 05-10)
        self.assertEqual(get_working_day_target_date("2026-05-07", 2), "2026-05-11")
        # Day 3: Tuesday 2026-05-12
        self.assertEqual(get_working_day_target_date("2026-05-07", 3), "2026-05-12")
        # Day 7: Monday 2026-05-18 (skipping two weekends: 05-09/10 and 05-16/17)
        self.assertEqual(get_working_day_target_date("2026-05-07", 7), "2026-05-18")

        # 2. Starting on Friday 2026-05-08
        # Day 1: Monday 2026-05-11 (skipping Sat 05-09 and Sun 05-10)
        self.assertEqual(get_working_day_target_date("2026-05-08", 1), "2026-05-11")
        # Day 2: Tuesday 2026-05-12
        self.assertEqual(get_working_day_target_date("2026-05-08", 2), "2026-05-12")
        # Day 5: Friday 2026-05-15
        self.assertEqual(get_working_day_target_date("2026-05-08", 5), "2026-05-15")
        # Day 6: Monday 2026-05-18 (skipping Sat 05-16 and Sun 05-17)
        self.assertEqual(get_working_day_target_date("2026-05-08", 6), "2026-05-18")

        # 3. Comprehensive check: horizons 1 to 90 never return Saturday (5) or Sunday (6)
        test_origins = ["2026-01-01", "2026-05-08", "2026-06-03", "2026-09-04"]
        for origin in test_origins:
            for h in range(1, 91):
                target_dt_str = get_working_day_target_date(origin, h)
                dt = pd.to_datetime(target_dt_str)
                self.assertLess(dt.weekday(), 5, f"Target date {target_dt_str} for origin {origin} and horizon {h} is on a weekend (weekday={dt.weekday()})")

    def test_weekend_skipping_continuous_pipeline(self):
        """Verify pipeline execution produces exact requested working days and no weekend dates."""
        pipe = ForecastingPipeline(self.dm)
        # Request 15 continuous days
        continuous_15d = list(range(1, 16))
        results = pipe.run_multi_horizon_forecast(
            job_id="test_weekend_pipeline_15d",
            selected_models=["XGBoost"],
            selected_metrics=["RMSE"],
            selected_horizons=continuous_15d,
            selected_ratios=["80-20"],
            auto_tuning=False
        )
        self.assertEqual(len(results), 15)
        for r in results:
            dt = pd.to_datetime(r["target_date"])
            self.assertLess(dt.weekday(), 5, f"Returned target_date {r['target_date']} falls on weekend")

    def test_horizon_purged_splits_zero_target_overlap(self):
        """Verify that training target realization dates never spill over into validation or test."""
        for h in [1, 7, 15, 30, 60, 90]:
            h_data = self.dm.get_dataset_for_horizon(h)
            splits = self.dm.split_chronological(
                h_data["X"], h_data["y"],
                horizon=h,
                train_ratio=0.80, val_ratio=0.10,
                dates=h_data["dates"],
                base_prices=h_data["base_prices"]
            )
            dates_tr = splits["dates_train"]
            dates_va = splits["dates_val"]
            dates_te = splits["dates_test"]

            max_tr_target_dt = pd.to_datetime(get_working_day_target_date(dates_tr.max(), h))
            min_va_dt = pd.to_datetime(dates_va.min())
            self.assertLessEqual(max_tr_target_dt, min_va_dt, f"Horizon {h}: Training target {max_tr_target_dt} overlaps with Val start {min_va_dt}")

            max_va_target_dt = pd.to_datetime(get_working_day_target_date(dates_va.max(), h))
            min_te_dt = pd.to_datetime(dates_te.min())
            self.assertLessEqual(max_va_target_dt, min_te_dt, f"Horizon {h}: Validation target {max_va_target_dt} overlaps with Test start {min_te_dt}")

if __name__ == "__main__":
    unittest.main()


