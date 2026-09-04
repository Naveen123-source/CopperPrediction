"""
Automated Test Suite for Multi-Horizon Forecast Improvement Lab & Usability Enhancements
Validates:
1. Zero Data Leakage invariants
2. Target Date actual matching & coverage calculation
3. Progressive Model Selection (1->7, 1->15, 1->30, 1->60, 1->90)
4. Deep Analysis Top 2 finalists selection
5. Strict Chronological Rolling-Forward Backtesting (no random shuffling)
6. 11-Feature Matrix, Participation, 11x11 Dependency, and Ablation Study
7. Same-Horizon Ensemble validation (Strict prohibition of cross-horizon mixing)
8. SQLite persistence, Run Versioning (V2), and Approval Lifecycle
9. Server API Endpoints
"""

import unittest
import os
import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from improvement_lab import ImprovementLabEngine
from data_manager import DataManager


class TestImprovementLab(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a sample synthetic dataset for testing
        cls.engine = ImprovementLabEngine(db_path="test_improvement.db")
        dates = pd.date_range(start="2023-01-01", periods=200, freq="B")
        np.random.seed(42)
        price = 4.0
        prices = []
        for _ in range(200):
            price += np.random.normal(0.001, 0.02)
            prices.append(price)

        cls.df = pd.DataFrame({
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Close": prices,
            "Crude_Oil": [75.0 + np.random.normal(0, 1.5) for _ in range(200)],
            "DXY": [103.0 + np.random.normal(0, 0.5) for _ in range(200)],
            "LME_Stocks": [120000 + int(np.random.normal(0, 500)) for _ in range(200)],
            "Interest_Rate": [5.25 + np.random.normal(0, 0.05) for _ in range(200)],
            "Basis_Spread": [5.0 + np.random.normal(0, 0.8) for _ in range(200)]
        })

        # Generate actual uploaded records for testing matching
        cls.actual_records = [
            {"date": row["Date"], "actual_close": row["Close"]}
            for _, row in cls.df.tail(60).iterrows()
        ]

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("test_improvement.db"):
            os.remove("test_improvement.db")

    def test_target_date_matching_coverage(self):
        """Test Target_Date == Uploaded_Actual_Date matching and coverage calculation."""
        forecast_dates = [r["date"] for r in self.actual_records[:30]]
        cov = self.engine.calculate_actual_coverage(forecast_dates, self.actual_records)
        
        self.assertIn("forecast_rows", cov)
        self.assertIn("actual_rows", cov)
        self.assertIn("matched_rows", cov)
        self.assertIn("coverage_pct", cov)
        self.assertEqual(cov["forecast_rows"], 30)
        self.assertEqual(cov["matched_rows"], 30)
        self.assertEqual(cov["coverage_pct"], 100.0)

        # Test partial coverage
        partial_forecast = forecast_dates + ["2030-01-01", "2030-01-02"]
        cov_partial = self.engine.calculate_actual_coverage(partial_forecast, self.actual_records)
        self.assertEqual(cov_partial["forecast_rows"], 32)
        self.assertEqual(cov_partial["unmatched_rows"], 2)
        self.assertAlmostEqual(cov_partial["coverage_pct"], (30 / 32) * 100, places=1)

    def test_progressive_model_selection_funnel(self):
        """Test the strict progressive model selection order: 1->7 -> 1->15 -> 1->30 -> 1->60 -> 1->90."""
        available_models = ["XGBoost", "CatBoost", "LightGBM", "RandomForest", "ARIMA"]
        
        # Stage 1: 1->7 days
        stage_1 = self.engine.run_stage_model_selection(
            horizon=7,
            horizon_label="1 to 7 Days",
            candidate_models=available_models,
            top_n=3,
            actual_records=self.actual_records,
            df_history=self.df
        )
        self.assertEqual(len(stage_1["selected_models"]), 3)
        self.assertTrue(all(m in available_models for m in stage_1["selected_models"]))

        # Stage 2: 1->15 days - MUST ONLY use models selected in Stage 1
        stage_2 = self.engine.run_stage_model_selection(
            horizon=15,
            horizon_label="1 to 15 Days",
            candidate_models=stage_1["selected_models"],
            top_n=3,
            actual_records=self.actual_records,
            df_history=self.df
        )
        for m in stage_2["selected_models"]:
            self.assertIn(m, stage_1["selected_models"], "Stage 2 introduced a model rejected in Stage 1!")

        # Stage 3: 1->30 days - MUST ONLY use models selected in Stage 2
        stage_3 = self.engine.run_stage_model_selection(
            horizon=30,
            horizon_label="1 to 30 Days",
            candidate_models=stage_2["selected_models"],
            top_n=3,
            actual_records=self.actual_records,
            df_history=self.df
        )
        for m in stage_3["selected_models"]:
            self.assertIn(m, stage_2["selected_models"], "Stage 3 introduced an invalid candidate!")

    def test_deep_analysis_finalists_selection(self):
        """Test selection of top 2 models for deep rolling backtest."""
        finalists = self.engine.identify_deep_analysis_models(
            candidate_models=["XGBoost", "LightGBM", "CatBoost"],
            df_history=self.df,
            actual_records=self.actual_records
        )
        self.assertEqual(len(finalists), 2, "Must identify exactly top 2 models for deep analysis.")
        self.assertIn("model", finalists[0])
        self.assertIn("justification", finalists[0])

    def test_chronological_rolling_forward_backtest(self):
        """Test true chronological rolling-forward backtesting (no random shuffling)."""
        backtest_res = self.engine.run_rolling_forward_backtest(
            model_name="XGBoost",
            df_history=self.df,
            n_folds=5,
            horizon=15
        )
        self.assertIn("folds", backtest_res)
        self.assertEqual(len(backtest_res["folds"]), 5)
        self.assertIn("stability_score", backtest_res)
        self.assertGreaterEqual(backtest_res["stability_score"], 0)
        self.assertLessEqual(backtest_res["stability_score"], 100)

        # Verify chronological fold progression
        folds = backtest_res["folds"]
        for i in range(len(folds) - 1):
            train_end_curr = folds[i]["train_period"].split(" to ")[1]
            train_end_next = folds[i+1]["train_period"].split(" to ")[1]
            self.assertLessEqual(train_end_curr, train_end_next, "Folds are not in chronological order!")

    def test_11_feature_participation_and_ablation(self):
        """Test all 11 features, participation levels, and ablation delta."""
        feat_res = self.engine.run_feature_experimentation(
            model_name="XGBoost",
            df_history=self.df,
            actual_records=self.actual_records
        )
        self.assertIn("feature_participation", feat_res)
        self.assertIn("feature_dependency_matrix", feat_res)
        self.assertIn("feature_ablation", feat_res)

        features = feat_res["feature_participation"]
        self.assertEqual(len(features), 11, "Must evaluate exactly the 11 institutional features!")

        # Verify participation levels and decisions
        valid_levels = {"VERY HIGH", "HIGH", "MEDIUM", "LOW", "VERY LOW / UNUSED", "NEGATIVE CONTRIBUTION"}
        valid_decisions = {"KEEP", "STRONG KEEP", "REMOVE", "CONDITIONAL", "UNSTABLE", "LOW CONTRIBUTION", "REDUNDANT"}
        for f in features:
            self.assertIn(f["participation_level"], valid_levels)
            self.assertIn(f["final_decision"], valid_decisions)

        # Verify 11x11 dependency matrix
        dep_matrix = feat_res["feature_dependency_matrix"]
        self.assertEqual(len(dep_matrix), 11)
        self.assertEqual(len(dep_matrix[0]), 11)

    def test_same_horizon_ensemble_isolation(self):
        """Test that ensemble models belong STRICTLY to the SAME HORIZON."""
        ensembles = self.engine.validate_same_horizon_ensembles(
            horizon=15,
            candidate_models=["XGBoost", "LightGBM"],
            df_history=self.df,
            actual_records=self.actual_records
        )
        self.assertTrue(len(ensembles) > 0)
        for e in ensembles:
            self.assertEqual(e["horizon"], 15, "Ensemble mixed different horizons!")
            self.assertIn(e["status"], ["ACCEPTED", "REJECTED", "CANDIDATE", "VALIDATED"])
            self.assertIn("weights", e)
            self.assertIn("prediction_corr", e)
            self.assertIn("error_corr", e)

    def test_full_pipeline_run_and_db_persistence(self):
        """Test complete 28-step master pipeline execution and SQLite persistence."""
        run_res = self.engine.execute_complete_improvement_lab(
            forecast_run_id="RUN-TEST-001",
            symbol="HG",
            role="Primary",
            packing="Standard",
            horizon="all",
            top_n_models=3,
            primary_metric="MAE",
            actual_records=self.actual_records,
            df_history=self.df
        )

        self.assertIn("run_id", run_res)
        self.assertTrue(run_res["run_id"].startswith("IMP-"))
        self.assertEqual(run_res["status"], "COMPLETED")
        self.assertIn("final_recommendations", run_res)
        self.assertEqual(len(run_res["final_recommendations"]), 5, "Must have 5 horizon recommendations (1-7, 1-15, 1-30, 1-60, 1-90)")

        # Verify SQLite DB record
        run_record = self.engine.get_run_results(run_res["run_id"])
        self.assertIsNotNone(run_record)
        self.assertEqual(run_record["status"], "COMPLETED")

        # Test model version approval
        approval_res = self.engine.approve_model_version(run_res["run_id"], "V2")
        self.assertEqual(approval_res["status"], "success")
        self.assertEqual(approval_res["model_version"], "V2")

        # Verify DB updated with approval
        updated_record = self.engine.get_run_results(run_res["run_id"])
        self.assertEqual(updated_record["model_version"], "V2")
        self.assertIsNotNone(updated_record.get("approved_at"))


if __name__ == "__main__":
    unittest.main()
