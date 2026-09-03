import urllib.request
import json

BASE_URL = "http://localhost:8000"

def test_comparison_ui():
    print("==================================================================")
    print("TEST 1: Validating Comparison UI HTML Elements")
    print("==================================================================")
    with urllib.request.urlopen(f"{BASE_URL}/") as resp:
        html = resp.read().decode("utf-8")

    # Banner controls
    assert 'id="chart-model-select"' in html, "chart-model-select missing"
    assert 'id="chart-ratio-select"' in html, "chart-ratio-select missing"
    assert 'id="chart-opt-metric-select"' in html, "chart-opt-metric-select missing"
    assert 'id="banner-perf-grade"' in html, "banner-perf-grade missing"
    assert 'id="forecast-range-controls"' in html, "forecast-range-controls missing"

    # Comparison metrics panel & filters
    assert 'id="forecast-comparison-metrics-panel"' in html, "forecast-comparison-metrics-panel missing"
    assert 'id="metric-view-tabs"' in html, "metric-view-tabs missing"
    assert 'data-view="all"' in html, "All Metrics tab missing"
    assert 'data-view="best"' in html, "Best Metrics tab missing"
    assert 'data-view="primary"' in html, "Primary Metrics tab missing"
    assert 'data-view="accuracy"' in html, "Accuracy Metrics tab missing"
    assert 'data-view="error"' in html, "Error Metrics tab missing"
    assert 'data-view="directional"' in html, "Directional Metrics tab missing"
    assert 'id="metric-single-select"' in html, "metric-single-select missing"
    assert 'id="metric-grade-select"' in html, "metric-grade-select missing"
    assert 'id="comp-metric-cards-grid"' in html, "comp-metric-cards-grid missing"
    print("[PASS] All comparison section HTML structure and filters verified.")

    print("\n==================================================================")
    print("TEST 2: Validating Comparison UI CSS Styling")
    print("==================================================================")
    with urllib.request.urlopen(f"{BASE_URL}/style.css") as resp:
        css = resp.read().decode("utf-8")

    assert ".forecast-comparison-metrics-panel" in css, ".forecast-comparison-metrics-panel missing in CSS"
    assert ".metric-filter-toolbar" in css, ".metric-filter-toolbar missing in CSS"
    assert ".metric-tab-pill" in css, ".metric-tab-pill missing in CSS"
    assert ".comparison-metric-cards-grid" in css, ".comparison-metric-cards-grid missing in CSS"
    assert ".metric-comp-card" in css, ".metric-comp-card missing in CSS"
    assert ".perf-tier-badge.tier-best" in css, ".perf-tier-badge.tier-best missing in CSS"
    assert ".perf-tier-badge.tier-good" in css, ".perf-tier-badge.tier-good missing in CSS"
    assert ".perf-tier-badge.tier-average" in css, ".perf-tier-badge.tier-average missing in CSS"
    assert ".perf-tier-badge.tier-poor" in css, ".perf-tier-badge.tier-poor missing in CSS"
    print("[PASS] Comparison metrics panel, tier badges, and card grid CSS verified.")

    print("\n==================================================================")
    print("TEST 3: Validating JavaScript Comparison Engine & Deduplication")
    print("==================================================================")
    with urllib.request.urlopen(f"{BASE_URL}/app.js?v=5") as resp:
        js = resp.read().decode("utf-8")

    assert "METRIC_DEFINITIONS" in js, "METRIC_DEFINITIONS missing in JS"
    assert "getMetricPerformanceTier" in js, "getMetricPerformanceTier missing in JS"
    assert "populateChartControlsDropdowns" in js, "populateChartControlsDropdowns missing in JS"
    assert "renderComparisonMetricsPanel" in js, "renderComparisonMetricsPanel missing in JS"
    assert "metricFilterCategory" in js, "metricFilterCategory missing in JS"
    assert "metricFilterSingle" in js, "metricFilterSingle missing in JS"
    assert "metricFilterGrade" in js, "metricFilterGrade missing in JS"
    print("[PASS] JavaScript comparison engine and filter logic verified.")

    print("\n>>> ALL COPPER FORECAST VS ACTUAL COMPARISON UI TESTS PASSED! <<<")

if __name__ == "__main__":
    test_comparison_ui()
