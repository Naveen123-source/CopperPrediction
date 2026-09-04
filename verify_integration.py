import sys
import json
import time
import urllib.request
import threading
import uvicorn

from server import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8008, log_level="warning")

BASE_URL = "http://127.0.0.1:8008"

def http_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as response:
        return response.status, response.read().decode("utf-8")

def http_post(path, data):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        return response.status, response.read().decode("utf-8")

def test_static_routes():
    print("Testing GET / ...")
    status, body = http_get("/")
    print(f"Status: {status}, Body len: {len(body)}")
    print(f"Body snippet: {body[:300]}")
    assert status == 200
    assert "COPPER FORECAST TERMINAL" in body
    assert "Forecast Improvement Lab" in body
    assert "RUN COMPLETE IMPROVEMENT LAB" in body
    print("[PASS] Static index.html served correctly with merged components.")

def test_api_config():
    print("Testing GET /api/config ...")
    status, body = http_get("/api/config")
    assert status == 200
    data = json.loads(body)["data"]
    assert len(data["models"]) == 9
    assert len(data["metrics"]) == 11
    assert "features" in data
    assert len(data["features"]) == 11
    print("[PASS] /api/config returned 9 models, 11 metrics, 11 features.")

def test_market_summary():
    print("Testing GET /api/market-summary ...")
    status, body = http_get("/api/market-summary")
    assert status == 200
    data = json.loads(body)["data"]
    assert "copper_close" in data
    assert "lme_stocks" in data
    print("[PASS] /api/market-summary returned valid market surveillance data.")

def test_historical_data():
    print("Testing GET /api/historical-data ...")
    status, body = http_get("/api/historical-data?limit=50")
    assert status == 200
    records = json.loads(body)["data"]
    assert len(records) > 0
    print(f"[PASS] /api/historical-data returned {len(records)} records.")

def test_improvement_endpoints():
    print("Testing GET /api/improvement/runs ...")
    status, body = http_get("/api/improvement/runs")
    assert status == 200
    data = json.loads(body)
    assert data["status"] == "success"
    print(f"[PASS] /api/improvement/runs returned {len(data['runs'])} historical runs.")

    print("Testing POST /api/improvement/check-actual-coverage ...")
    status, body = http_post("/api/improvement/check-actual-coverage", {"actual_records": [
        {"Target_Date": "2024-01-02", "Actual_Price": 3.85},
        {"Target_Date": "2024-01-03", "Actual_Price": 3.88}
    ]})
    assert status == 200
    res = json.loads(body)
    assert "actual_rows" in res
    assert res["actual_rows"] == 2
    print("[PASS] /api/improvement/check-actual-coverage responded correctly.")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Wait for server startup

    try:
        test_static_routes()
        test_api_config()
        test_market_summary()
        test_historical_data()
        test_improvement_endpoints()
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
