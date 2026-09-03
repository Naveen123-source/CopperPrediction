import urllib.request
import json
import time

def run_verification():
    print("==========================================================================")
    print("RUNNING COMPREHENSIVE PIPELINE VERIFICATION")
    print("==========================================================================")
    
    # 1. Test Fixed Horizons across all 9 models
    print("\n--- Test 1: All 9 Models across Key Horizons [1, 7, 15, 30, 60, 90] ---")
    req_data = {
        "models": ["XGBoost", "CatBoost", "LightGBM", "RandomForest", "Stacking Ensemble", "Stage Regression", "ARIMA", "SARIMAX", "LSTM"],
        "metrics": ["RMSE", "MAE", "R²", "MAPE"],
        "horizons": [1, 7, 15, 30, 60, 90],
        "ratios": ["80-20"],
        "auto_tuning": False
    }
    req = urllib.request.Request(
        "http://localhost:8000/api/forecast/run",
        data=json.dumps(req_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    job = json.loads(res.read().decode("utf-8"))
    job_id = job["job_id"]
    print(f"Job ID: {job_id} | Experiments: {job['total_experiments']}")

    while True:
        res = urllib.request.urlopen(f"http://localhost:8000/api/forecast/status/{job_id}")
        st = json.loads(res.read().decode("utf-8"))
        if st["status"] in ["COMPLETED", "ERROR"]:
            print(f"Job Status: {st['status']} ({st['completed']}/{st['total']})")
            break
        time.sleep(0.5)

    res = urllib.request.urlopen(f"http://localhost:8000/api/forecast/results/{job_id}")
    cards = json.loads(res.read().decode("utf-8"))["results"]
    print(f"\nReceived {len(cards)} result cards.")
    
    # Print sample cards for 7-Day and 30-Day horizon
    print("\nSample 7-Day Forecast Cards:")
    h7_cards = [c for c in cards if c["horizon"] == 7 and c["metric_name"] == "RMSE"]
    for c in h7_cards:
        print(f"  {c['model']:20s} -> Predicted Price: ${c['predicted_price']:.4f} (Origin: ${c['latest_price']:.4f}, Target Date: {c['target_date']}) | RMSE: {c['metric_score']:.4f} | R²: {c['all_metrics']['R²']:.4f} | Leakage: {c['leakage_check']}")
        assert c["leakage_check"] == "PASS"
        assert c["predicted_price"] > 5.0 # Must not crash to $4.77

    print("\nSample 30-Day Forecast Cards:")
    h30_cards = [c for c in cards if c["horizon"] == 30 and c["metric_name"] == "RMSE"]
    for c in h30_cards:
        print(f"  {c['model']:20s} -> Predicted Price: ${c['predicted_price']:.4f} (Origin: ${c['latest_price']:.4f}, Target Date: {c['target_date']}) | RMSE: {c['metric_score']:.4f} | R²: {c['all_metrics']['R²']:.4f} | Leakage: {c['leakage_check']}")
        assert c["leakage_check"] == "PASS"
        assert c["predicted_price"] > 5.0

    # 2. Test Continuous Daily Range (1 to 7 Days)
    print("\n--- Test 2: Continuous Daily Range (1 to 7 Days) ---")
    req_data_cont = {
        "models": ["XGBoost", "CatBoost", "Stacking Ensemble"],
        "metrics": ["RMSE"],
        "horizons": [1, 2, 3, 4, 5, 6, 7],
        "ratios": ["80-20"],
        "auto_tuning": False
    }
    req2 = urllib.request.Request(
        "http://localhost:8000/api/forecast/run",
        data=json.dumps(req_data_cont).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res2 = urllib.request.urlopen(req2)
    job2 = json.loads(res2.read().decode("utf-8"))
    job_id2 = job2["job_id"]

    while True:
        res = urllib.request.urlopen(f"http://localhost:8000/api/forecast/status/{job_id2}")
        st = json.loads(res.read().decode("utf-8"))
        if st["status"] in ["COMPLETED", "ERROR"]:
            break
        time.sleep(0.3)

    res = urllib.request.urlopen(f"http://localhost:8000/api/forecast/results/{job_id2}")
    cont_cards = json.loads(res.read().decode("utf-8"))["results"]
    print(f"Continuous Day-by-Day Results (Total: {len(cont_cards)} cards):")
    for c in cont_cards[:7]:
        print(f"  {c['model']} | {c['horizon_label']} (Target {c['target_date']}) -> Predicted Price: ${c['predicted_price']:.4f} | RMSE: {c['metric_score']:.4f}")
        assert c["predicted_price"] > 5.0

    print("\n==========================================================================")
    print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
    print("==========================================================================")

if __name__ == "__main__":
    run_verification()
