import urllib.request
import json
import time

def test():
    # 1. Test Config
    res = urllib.request.urlopen("http://localhost:8000/api/config")
    cfg = json.loads(res.read().decode("utf-8"))
    print("Continuous Ranges:", list(cfg["continuous_ranges"].keys()))

    # 2. Test Continuous Direct Run (1 to 7 Days)
    req_data = {
        "models": ["XGBoost", "CatBoost"],
        "metrics": ["RMSE", "MAE"],
        "horizons": [1, 2, 3, 4, 5, 6, 7],
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
    print(f"Job Started: {job_id} | Total Experiments: {job['total_experiments']}")

    while True:
        res = urllib.request.urlopen(f"http://localhost:8000/api/forecast/status/{job_id}")
        st = json.loads(res.read().decode("utf-8"))
        if st["status"] in ["COMPLETED", "ERROR"]:
            print("Job Status:", st["status"])
            break
        time.sleep(0.3)

    res = urllib.request.urlopen(f"http://localhost:8000/api/forecast/results/{job_id}")
    cards = json.loads(res.read().decode("utf-8"))["results"]
    print(f"\nReceived {len(cards)} individual direct daily cards (2 models * 7 days * 1 ratio * 2 metrics = 28 cards):")
    for c in cards[:14]: # Print sample Day 1..Day 7 for first model
        print(f"  {c['model']} | {c['horizon_label']} (Target {c['target_date']}) -> Predicted: ${c['predicted_price']:.4f} | {c['metric_name']}: {c['metric_score']} | Leakage: {c['leakage_check']}")
        assert c["leakage_check"] == "PASS"

    print("\n[PASS] Continuous day-by-day direct multi-horizon forecasting successfully verified!")

if __name__ == "__main__":
    test()
