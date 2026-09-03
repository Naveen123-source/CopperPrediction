import time
import requests
import io
import pandas as pd

def run_e2e_test():
    base_url = "http://127.0.0.1:8000"
    
    # 1. Run Forecast
    payload = {
        "models": ["XGBoost"],
        "metrics": ["RMSE"],
        "horizons": [1, 2, 3, 4, 5, 6, 7],
        "ratios": ["80-20"],
        "auto_tuning": False
    }
    res = requests.post(f"{base_url}/api/forecast/run", json=payload)
    assert res.status_code == 200, f"Forecast start failed: {res.text}"
    job_id = res.json()["job_id"]
    print(f"Forecast started: {job_id}")

    # 2. Wait for completion
    for _ in range(30):
        status_res = requests.get(f"{base_url}/api/forecast/status/{job_id}").json()
        if status_res.get("status") == "COMPLETED":
            break
        time.sleep(0.5)
    
    results_res = requests.get(f"{base_url}/api/forecast/results/{job_id}").json()
    assert results_res["status"] == "COMPLETED"
    results = results_res["results"]
    print(f"Forecast completed with {len(results)} horizon cards.")

    target_dates = [r["target_date"] for r in results]
    print(f"Target Dates: {target_dates}")

    # 3. Create Sample Actual Data CSV for the first 5 target dates (partial upload test)
    actual_rows = []
    for i, dt in enumerate(target_dates[:5]):
        pred_p = results[i]["predicted_price"]
        actual_rows.append({
            "Date": dt,
            "Copper_Open": pred_p - 0.02,
            "Copper_High": pred_p + 0.03,
            "Copper_Low": pred_p - 0.03,
            "Copper_Close": round(pred_p + 0.015 * (1 if i % 2 == 0 else -1), 4),
            "Copper_Volume": 1000 + i * 50,
            "Crude_Oil": 82.5,
            "DXY": 100.1,
            "Interest_Rate": 4.65,
            "LME_Stocks": 93500,
            "Basis_Spread": 25.0
        })
    df_actual = pd.DataFrame(actual_rows)
    csv_bytes = df_actual.to_csv(index=False).encode("utf-8")

    # 4. Upload Actual Data to endpoint
    files = {"file": ("actual_copper_market.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_res = requests.post(f"{base_url}/api/forecast/upload-actual", files=files)
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    uploaded_json = upload_res.json()
    print("Upload parsed successfully:", uploaded_json)

    # 5. Verify Date Matching
    actual_map = {r["date"]: r["actual_close"] for r in uploaded_json["records"]}
    matched = []
    for r in results:
        if r["target_date"] in actual_map:
            matched.append({"pred": r["predicted_price"], "actual": actual_map[r["target_date"]]})

    print(f"Matched count: {len(matched)} / {len(results)}")
    assert len(matched) == 5, f"Expected 5 matched days, got {len(matched)}"
    print("E2E Actual Data Upload and Comparison test passed successfully!")

if __name__ == "__main__":
    run_e2e_test()
