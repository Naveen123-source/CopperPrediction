"""
Multi-Horizon Forecasting Execution Pipeline
Orchestrates experiments across:
Selected Model × Forecast Horizon × Train/Test Ratio × Selected Error Metric
With live progress streaming, leakage audits, and future forecasting.
"""

import time
import uuid
import datetime
import threading
import numpy as np
import pandas as pd

from data_manager import DataManager, FORECAST_HORIZONS, RATIOS_CONFIG, get_working_day_target_date
from metrics import calculate_all_metrics, ALL_METRICS
from leakage_guard import LeakageGuard
from models import MODEL_REGISTRY
from tuner import MetricSpecificTuner

class ForecastingPipeline:
    def __init__(self, data_manager=None):
        self.data_manager = data_manager or DataManager()
        self.tuner = MetricSpecificTuner(n_splits=3)
        self.active_jobs = {}
        self.results_cache = {}
        self.is_cancelled = False
        
    def cancel_job(self, job_id):
        if job_id in self.active_jobs:
            self.active_jobs[job_id]["status"] = "CANCELLED"
            self.is_cancelled = True
            
    def run_multi_horizon_forecast(
        self,
        job_id,
        selected_models=None,
        selected_metrics=None,
        selected_horizons=None,
        selected_ratios=None,
        auto_tuning=False,
        progress_callback=None
    ):
        """
        Executes multi-horizon forecasting experiments synchronously or within a worker thread.
        Emits real-time progress events via progress_callback.
        """
        self.is_cancelled = False
        selected_models = selected_models or list(MODEL_REGISTRY.keys())
        selected_metrics = selected_metrics or ["RMSE", "MAE"]
        selected_horizons = selected_horizons or FORECAST_HORIZONS
        selected_ratios = selected_ratios or list(RATIOS_CONFIG.keys())
        
        # Calculate total experiments
        total_experiments = len(selected_models) * len(selected_horizons) * len(selected_ratios) * len(selected_metrics)
        completed_count = 0
        
        self.active_jobs[job_id] = {
            "status": "RUNNING",
            "progress": 0.0,
            "completed": 0,
            "total": total_experiments,
            "current_model": "",
            "current_horizon": "",
            "current_ratio": "",
            "current_metric": "",
            "results": [],
            "error": None
        }
        
        all_results = []
        start_time = time.time()
        
        try:
            # Audit causal features once
            feature_audit = LeakageGuard.audit_features(self.data_manager.processed_df)
            
            for horizon in selected_horizons:
                if self.is_cancelled:
                    break
                    
                horizon_data = self.data_manager.get_dataset_for_horizon(horizon)
                X_full = horizon_data["X"]
                y_full = horizon_data["y"]
                dates_full = horizon_data["dates"]
                base_prices_full = horizon_data["base_prices"]
                X_latest = horizon_data["X_latest"]
                latest_date = horizon_data["latest_date"]
                latest_base_price = horizon_data["latest_base_price"]
                
                # Target future forecast date (strictly working days: skips Saturday and Sunday)
                target_date = get_working_day_target_date(latest_date, horizon)
                
                for ratio_key in selected_ratios:
                    if self.is_cancelled:
                        break
                        
                    train_ratio = RATIOS_CONFIG.get(ratio_key, 0.80)
                    splits = self.data_manager.split_chronological(
                        X_full, y_full,
                        horizon=horizon,
                        train_ratio=train_ratio,
                        val_ratio=0.10,
                        dates=dates_full,
                        base_prices=base_prices_full
                    )
                    
                    X_train, y_train = splits["X_train"], splits["y_train"]
                    X_val, y_val = splits["X_val"], splits["y_val"]
                    X_test, y_test = splits["X_test"], splits["y_test"]
                    dates_train, dates_test = splits["dates_train"], splits["dates_test"]
                    base_train, base_test = splits["base_train"], splits["base_test"]
                    
                    # Actual ground truth future prices at t+h for test set
                    y_test_actual = base_test.values + y_test.values
                    
                    split_audit = LeakageGuard.audit_splits(dates_train, splits["dates_val"], dates_test, horizon=horizon)
                    
                    for model_name in selected_models:
                        if self.is_cancelled:
                            break
                            
                        model_cls = MODEL_REGISTRY.get(model_name)
                        if not model_cls:
                            continue
                            
                        # If auto_tuning is disabled, predictions for a (model, horizon, ratio) can be generated once
                        cached_pred_prices = None
                        cached_future_price = None
                        cached_all_metrics = None
                        
                        for metric_name in selected_metrics:
                            if self.is_cancelled:
                                break
                                
                            self.active_jobs[job_id]["current_model"] = model_name
                            self.active_jobs[job_id]["current_horizon"] = f"{horizon} Days"
                            self.active_jobs[job_id]["current_ratio"] = ratio_key
                            self.active_jobs[job_id]["current_metric"] = metric_name
                            
                            best_params = {}
                            if auto_tuning:
                                # Independent tuning for each metric on reconstructed prices
                                best_params = self.tuner.tune(
                                    model_name=model_name,
                                    horizon=horizon,
                                    target_metric=metric_name,
                                    X_train=X_train,
                                    y_train=y_train,
                                    base_train=base_train
                                )
                                model_instance = model_cls(horizon=horizon, params=best_params)
                                model_instance.fit(X_train, y_train)
                                test_pred_deltas = model_instance.predict(X_test)
                                test_pred_prices = base_test.values + test_pred_deltas
                                
                                future_pred_delta = float(model_instance.predict(X_latest)[0])
                                future_pred_price = latest_base_price + future_pred_delta
                                
                                metrics_dict = calculate_all_metrics(y_test_actual, test_pred_prices, y_base=base_test.values)
                            else:
                                if cached_pred_prices is None:
                                    model_instance = model_cls(horizon=horizon)
                                    model_instance.fit(X_train, y_train)
                                    test_pred_deltas = model_instance.predict(X_test)
                                    cached_pred_prices = base_test.values + test_pred_deltas
                                    
                                    future_pred_delta = float(model_instance.predict(X_latest)[0])
                                    cached_future_price = latest_base_price + future_pred_delta
                                    
                                    cached_all_metrics = calculate_all_metrics(y_test_actual, cached_pred_prices, y_base=base_test.values)
                                    best_params = model_instance.get_params()
                                    
                                test_pred_prices = cached_pred_prices
                                future_pred_price = cached_future_price
                                metrics_dict = cached_all_metrics
                                
                            primary_score = metrics_dict.get(metric_name, 0.0)
                            
                            # Build Result Card Item
                            result_card = {
                                "id": f"{model_name}_{horizon}D_{ratio_key}_{metric_name.replace(' ', '_')}",
                                "model": model_name,
                                "horizon": horizon,
                                "horizon_label": f"{horizon} Day{'s' if horizon > 1 else ''}",
                                "ratio": ratio_key,
                                "metric_name": metric_name,
                                "metric_score": primary_score,
                                "predicted_price": round(future_pred_price, 4),
                                "target_date": target_date,
                                "latest_price": round(latest_base_price, 4),
                                "price_change": round(future_pred_price - latest_base_price, 4),
                                "price_change_pct": round(((future_pred_price - latest_base_price) / (latest_base_price + 1e-8)) * 100, 2),
                                "auto_tuned": "Yes" if auto_tuning else "No",
                                "best_params": best_params,
                                "train_period": split_audit.get("train_period", "N/A"),
                                "val_period": split_audit.get("val_period", "N/A"),
                                "test_period": split_audit.get("test_period", "N/A"),
                                "leakage_check": "PASS" if (split_audit["status"] == "PASS" and feature_audit["status"] == "PASS") else "FAIL",
                                "all_metrics": metrics_dict,
                                "test_actual_sample": [round(float(v), 4) for v in y_test_actual[-30:]] if len(y_test_actual) >= 30 else [round(float(v), 4) for v in y_test_actual],
                                "test_pred_sample": [round(float(v), 4) for v in test_pred_prices[-30:]] if len(test_pred_prices) >= 30 else [round(float(v), 4) for v in test_pred_prices],
                                "test_dates_sample": [d.strftime("%Y-%m-%d") for d in dates_test.iloc[-30:]] if len(dates_test) >= 30 else [d.strftime("%Y-%m-%d") for d in dates_test]
                            }
                            
                            all_results.append(result_card)
                            completed_count += 1
                            
                            progress_pct = round((completed_count / total_experiments) * 100, 1)
                            self.active_jobs[job_id]["progress"] = progress_pct
                            self.active_jobs[job_id]["completed"] = completed_count
                            
                            if progress_callback:
                                progress_callback({
                                    "job_id": job_id,
                                    "status": "RUNNING",
                                    "progress": progress_pct,
                                    "completed": completed_count,
                                    "total": total_experiments,
                                    "model": model_name,
                                    "horizon": f"{horizon} Days",
                                    "ratio": ratio_key,
                                    "metric": metric_name,
                                    "latest_card": result_card
                                })

            if self.is_cancelled:
                self.active_jobs[job_id]["status"] = "CANCELLED"
            else:
                self.active_jobs[job_id]["status"] = "COMPLETED"
                self.active_jobs[job_id]["progress"] = 100.0
                self.active_jobs[job_id]["results"] = all_results
                self.results_cache[job_id] = all_results
                
            elapsed = round(time.time() - start_time, 2)
            self.active_jobs[job_id]["elapsed_seconds"] = elapsed
            
            if progress_callback:
                progress_callback({
                    "job_id": job_id,
                    "status": self.active_jobs[job_id]["status"],
                    "progress": 100.0 if not self.is_cancelled else self.active_jobs[job_id]["progress"],
                    "completed": completed_count,
                    "total": total_experiments,
                    "elapsed_seconds": elapsed,
                    "results_count": len(all_results)
                })
                
        except Exception as e:
            self.active_jobs[job_id]["status"] = "ERROR"
            self.active_jobs[job_id]["error"] = str(e)
            if progress_callback:
                progress_callback({
                    "job_id": job_id,
                    "status": "ERROR",
                    "error": str(e)
                })
            raise e
            
        return all_results
