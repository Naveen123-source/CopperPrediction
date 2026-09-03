import urllib.request
import json
import re

BASE_URL = "http://localhost:8000"

def test_ui_and_api():
    print("==================================================================")
    print("TEST 1: Validating HTML Structure for Grid View & Pagination")
    print("==================================================================")
    with urllib.request.urlopen(f"{BASE_URL}/") as resp:
        html = resp.read().decode("utf-8")

    assert 'id="results-grid-container"' in html, "results-grid-container missing in HTML"
    assert 'id="results-data-grid"' in html, "results-data-grid missing in HTML"
    assert 'id="results-grid-body"' in html, "results-grid-body missing in HTML"
    assert 'id="grid-pagination-bar"' in html, "grid-pagination-bar missing in HTML"
    assert 'id="grid-page-size-select"' in html, "grid-page-size-select missing in HTML"
    assert 'id="btn-pag-first"' in html, "btn-pag-first missing in HTML"
    assert 'id="btn-pag-prev"' in html, "btn-pag-prev missing in HTML"
    assert 'id="btn-pag-next"' in html, "btn-pag-next missing in HTML"
    assert 'id="btn-pag-last"' in html, "btn-pag-last missing in HTML"
    assert 'id="card-expand-modal"' in html, "card-expand-modal missing in HTML"
    assert "Actual Price" in html, "Actual Price missing in table headers"
    assert "Difference ($)" in html, "Difference ($) missing in table headers"
    assert "Direction Match" in html, "Direction Match missing in table headers"
    print("[PASS] HTML elements for Results Grid, Actual Data columns & Pagination verified.")

    print("\n==================================================================")
    print("TEST 2: Validating CSS Styling")
    print("==================================================================")
    with urllib.request.urlopen(f"{BASE_URL}/style.css") as resp:
        css = resp.read().decode("utf-8")

    assert ".results-grid-container" in css, ".results-grid-container missing in CSS"
    assert ".results-data-grid" in css, ".results-data-grid missing in CSS"
    assert ".btn-grid-chart-action" in css, ".btn-grid-chart-action missing in CSS"
    assert ".grid-pagination-bar" in css, ".grid-pagination-bar missing in CSS"
    assert ".pag-btn" in css, ".pag-btn missing in CSS"
    assert ".col-actual-price" in css, ".col-actual-price missing in CSS"
    print("[PASS] CSS styles for Results Grid, Buttons, and Pagination verified.")

    print("\n==================================================================")
    print("TEST 3: Validating JavaScript Code")
    print("==================================================================")
    with urllib.request.urlopen(f"{BASE_URL}/app.js?v=4") as resp:
        js = resp.read().decode("utf-8")

    assert "calculateTotalPages" in js, "calculateTotalPages missing in JS"
    assert "renderResultsGridPage" in js, "renderResultsGridPage missing in JS"
    assert "updatePaginationUI" in js, "updatePaginationUI missing in JS"
    assert "openCardExpandModal" in js, "openCardExpandModal missing in JS"
    assert "btn-grid-chart-action" in js, "btn-grid-chart-action missing in JS"
    print("[PASS] JavaScript Grid rendering & Pagination functions verified.")

    print("\n==================================================================")
    print("TEST 4: Running Multi-Horizon Forecast & Verifying Data Payload")
    print("==================================================================")
    payload = {
        "models": ["XGBoost", "CatBoost", "LightGBM"],
        "metrics": ["RMSE", "MAE"],
        "horizons": [1, 7, 15, 30],
        "ratios": ["70-30", "80-20"],
        "auto_tuning": False
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/forecast/run",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    
    assert res["status"] == "started"
    job_id = res["job_id"]
    print(f"  Job ID: {job_id} ({res['total_experiments']} experiments)")

    import time
    while True:
        with urllib.request.urlopen(f"{BASE_URL}/api/forecast/status/{job_id}") as resp:
            st = json.loads(resp.read().decode("utf-8"))
            if st["status"] in ["COMPLETED", "ERROR", "CANCELLED"]:
                assert st["status"] == "COMPLETED", f"Forecast job failed: {st}"
                break
        time.sleep(0.3)

    with urllib.request.urlopen(f"{BASE_URL}/api/forecast/results/{job_id}") as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
    
    results = res_data["results"]
    print(f"[PASS] Forecast completed. Received {len(results)} records.")
    
    # Check that required grid row fields exist
    first_record = results[0]
    required_fields = [
        "model", "horizon", "horizon_label", "ratio", "target_date",
        "predicted_price", "price_change", "price_change_pct", "latest_price",
        "metric_name", "metric_score", "all_metrics", "leakage_check",
        "auto_tuned", "train_period", "val_period", "test_period"
    ]
    for f in required_fields:
        assert f in first_record, f"Field {f} missing in forecast result record"

    print(f"  Sample Row 1: Model={first_record['model']}, Horizon={first_record['horizon_label']}, Date={first_record['target_date']}, Price=${first_record['predicted_price']:.4f}, Metric={first_record['metric_name']}:{first_record['metric_score']}")
    print("\n>>> ALL MULTI-HORIZON RESULTS DATA GRID TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_ui_and_api()
