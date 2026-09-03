"""
End-to-End API & Dashboard Verification Script
Validates all endpoints, UI HTML payload, market cards data, and multi-horizon forecasting pipeline.
"""

import time
import json
import urllib.request

BASE_URL = "http://localhost:8000"

def test_endpoint(url, method="GET", data=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers={"Content-Type": "application/json"} if data else {},
        method=method
    )
    with urllib.request.urlopen(req) as response:
        content = response.read().decode("utf-8")
        try:
            return response.status, json.loads(content)
        except Exception:
            return response.status, content

def main():
    print("==========================================================")
    print("STEP 1: Validating UI Landing Page & Static Assets")
    print("==========================================================")
    status, html = test_endpoint(f"{BASE_URL}/")
    assert status == 200, f"HTML returned status {status}"
    assert "COPPER FORECAST TERMINAL" in html
    assert "Copper Open" in html
    assert "Copper Close" in html
    assert "Crude Oil (WTI)" in html
    assert "LME Copper Stock" in html
    assert "US Dollar Index (DXY)" in html
    assert "US 10Y Interest Rate" in html
    assert "ZERO LEAKAGE ENGINE" in html
    assert "Run Multi-Horizon Forecast" in html
    print("[PASS] HTML Page loaded with all Yahoo Finance market dashboard components.")

    print("\n==========================================================")
    print("STEP 2: Validating Market Summary API (/api/market-summary)")
    print("==========================================================")
    status, res = test_endpoint(f"{BASE_URL}/api/market-summary")
    assert status == 200 and res["status"] == "success"
    d = res["data"]
    print(f"  Copper Open:    ${d['copper_open']:.4f}")
    print(f"  Copper High:    ${d['copper_high']:.4f}")
    print(f"  Copper Low:     ${d['copper_low']:.4f}")
    print(f"  Copper Close:   ${d['copper_close']:.4f} ({d['copper_change']:+.4f} / {d['copper_pct_change']:+.2f}%)")
    print(f"  LME Stock:      {d['copper_stock']:,} MT")
    print(f"  Crude Oil:      ${d['crude_oil']:.2f}/bbl")
    print(f"  DXY Index:      {d['dxy_index']:.2f}")
    print(f"  Interest Rate:  {d['interest_rate']:.2f}%")
    print(f"  Basis Spread:   ${d['basis_spread']:.2f}/t")
    print("[PASS] Market Summary cards API verified.")

    print("\n==========================================================")
    print("STEP 3: Validating Historical Time-Series API (/api/historical-data)")
    print("==========================================================")
    status, res = test_endpoint(f"{BASE_URL}/api/historical-data?limit=50")
    assert status == 200 and res["status"] == "success"
    assert len(res["data"]) == 50
    print(f"[PASS] Historical records verified ({len(res['data'])} daily OHLC bars returned).")

    print("\n==========================================================")
    print("STEP 4: Validating Multi-Horizon Direct Forecasting Engine")
    print("==========================================================")
    # Test with multiple models, direct horizons (1, 7, 15, 30, 60, 90), ratios, and metrics
    payload = {
        "models": ["XGBoost", "CatBoost", "LightGBM", "RandomForest", "Stacking Ensemble", "Stage Regression", "ARIMA", "SARIMAX", "LSTM"],
        "metrics": ["RMSE", "MAE", "Directional Accuracy", "MAPE"],
        "horizons": [1, 7, 15, 30, 60, 90],
        "ratios": ["70-30", "80-20"],
        "auto_tuning": False
    }
    status, res = test_endpoint(f"{BASE_URL}/api/forecast/run", method="POST", data=payload)
    assert status == 200 and res["status"] == "started"
    job_id = res["job_id"]
    print(f"  Started Job: {job_id} ({res['total_experiments']} total experiment combinations)")

    # Poll status until complete
    while True:
        status, status_res = test_endpoint(f"{BASE_URL}/api/forecast/status/{job_id}")
        progress = status_res["progress"]
        completed = status_res["completed"]
        total = status_res["total"]
        cur_model = status_res.get("current_model", "")
        cur_horizon = status_res.get("current_horizon", "")
        cur_metric = status_res.get("current_metric", "")
        print(f"  Progress: {progress:.1f}% | {completed}/{total} | {cur_model} ({cur_horizon}, {cur_metric})", end="\r")
        
        if status_res["status"] in ["COMPLETED", "ERROR", "CANCELLED"]:
            print(f"\n  Final Status: {status_res['status']}")
            break
        time.sleep(0.4)

    assert status_res["status"] == "COMPLETED"

    # Fetch and check results
    status, results_res = test_endpoint(f"{BASE_URL}/api/forecast/results/{job_id}")
    cards = results_res["results"]
    print(f"  Total Result Cards Generated: {len(cards)}")
    assert len(cards) == res["total_experiments"]

    # Sample check first 5 cards
    print("\n--- SAMPLE RESULT CARDS ---")
    for i, c in enumerate(cards[:5]):
        print(f"Card #{i+1}:")
        print(f"  Model:            {c['model']}")
        print(f"  Forecast Horizon: {c['horizon_label']}")
        print(f"  Train/Test Ratio: {c['ratio']}")
        print(f"  Target Date:      {c['target_date']}")
        print(f"  Predicted Price:  ${c['predicted_price']:.4f} (Change: {c['price_change']:+.4f})")
        print(f"  Target Metric:    {c['metric_name']} = {c['metric_score']}")
        print(f"  Leakage Check:    {c['leakage_check']}")
        print(f"  All 11 Metrics:   MAE={c['all_metrics']['MAE']}, RMSE={c['all_metrics']['RMSE']}, R2={c['all_metrics']['R²']}, DirAcc={c['all_metrics']['Directional Accuracy']}%")
        print("--------------------------------------------------")
        assert c["leakage_check"] == "PASS"
        assert len(c["all_metrics"]) == 11

    print("\n==========================================================")
    print("STEP 5: Validating Metric-Specific Auto-Tuning Run")
    print("==========================================================")
    tuning_payload = {
        "models": ["XGBoost", "Stage Regression"],
        "metrics": ["RMSE", "MAE"],
        "horizons": [1, 30],
        "ratios": ["80-20"],
        "auto_tuning": True
    }
    status, res = test_endpoint(f"{BASE_URL}/api/forecast/run", method="POST", data=tuning_payload)
    job_id_tune = res["job_id"]
    print(f"  Started Auto-Tuning Job: {job_id_tune}")
    
    while True:
        status, status_res = test_endpoint(f"{BASE_URL}/api/forecast/status/{job_id_tune}")
        if status_res["status"] in ["COMPLETED", "ERROR", "CANCELLED"]:
            print(f"  Auto-Tuning Status: {status_res['status']}")
            break
        time.sleep(0.4)
        
    status, results_tune = test_endpoint(f"{BASE_URL}/api/forecast/results/{job_id_tune}")
    for c in results_tune["results"]:
        assert c["auto_tuned"] == "Yes"
        print(f"  {c['model']} | Horizon {c['horizon_label']} | Metric: {c['metric_name']} -> Best Params: {c['best_params']}")

    print("\n==========================================================")
    print("ALL API AND MULTI-HORIZON PIPELINE VALIDATIONS PASSED (100%)")
    print("==========================================================")

if __name__ == "__main__":
    main()
