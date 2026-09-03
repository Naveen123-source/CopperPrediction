import unittest
import numpy as np

def calculate_comparison_metrics(matched_pairs, origin_price=None):
    if not matched_pairs:
        return None
    n = len(matched_pairs)
    preds = np.array([p['pred'] for p in matched_pairs])
    actuals = np.array([p['actual'] for p in matched_pairs])

    errors = preds - actuals
    abs_errors = np.abs(errors)
    sq_errors = errors ** 2

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(sq_errors)))
    mape = float(np.mean(abs_errors / (actuals + 1e-8)) * 100)
    smape = float(np.mean(abs_errors / ((np.abs(actuals) + np.abs(preds)) / 2 + 1e-8)) * 100)

    ss_tot = float(np.sum((actuals - np.mean(actuals)) ** 2))
    ss_res = float(np.sum(sq_errors))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    mean_error = float(np.mean(errors))
    max_abs_error = float(np.max(abs_errors))
    error_std_dev = float(np.std(errors, ddof=1)) if n > 1 else 0.0

    origin = origin_price if origin_price is not None else actuals[0]
    dir_acc = float(np.mean(np.sign(preds - origin) == np.sign(actuals - origin)) * 100)

    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "MAPE": round(mape, 2),
        "sMAPE": round(smape, 2),
        "R²": round(r2, 4),
        "Mean Error (Bias)": round(mean_error, 4),
        "Directional Accuracy": round(dir_acc, 1),
        "Max Absolute Error": round(max_abs_error, 4),
        "Error Std Dev": round(error_std_dev, 4)
    }

class TestActualDataComparison(unittest.TestCase):
    def test_exact_match(self):
        forecast = [
            {"date": "2026-08-11", "pred": 6.612},
            {"date": "2026-08-12", "pred": 6.597},
            {"date": "2026-08-13", "pred": 6.592}
        ]
        actual = [
            {"date": "2026-08-11", "actual": 6.612},
            {"date": "2026-08-12", "actual": 6.597},
            {"date": "2026-08-13", "actual": 6.592}
        ]
        matched = [{"pred": f["pred"], "actual": a["actual"]} for f, a in zip(forecast, actual)]
        metrics = calculate_comparison_metrics(matched, origin_price=6.60)
        self.assertEqual(metrics["MAE"], 0.0)
        self.assertEqual(metrics["RMSE"], 0.0)
        self.assertEqual(metrics["MAPE"], 0.0)
        self.assertEqual(metrics["R²"], 1.0)
        self.assertEqual(metrics["Directional Accuracy"], 100.0)

    def test_partial_match(self):
        forecast = [
            {"date": "2026-08-11", "pred": 6.60},
            {"date": "2026-08-12", "pred": 6.62},
            {"date": "2026-08-13", "pred": 6.65},
            {"date": "2026-08-14", "pred": 6.68},
            {"date": "2026-08-15", "pred": 6.70}
        ]
        # Only 3 days observed out of 5
        actual_map = {
            "2026-08-11": 6.58,
            "2026-08-12": 6.61,
            "2026-08-13": 6.66
        }
        matched = []
        for f in forecast:
            if f["date"] in actual_map:
                matched.append({"pred": f["pred"], "actual": actual_map[f["date"]]})

        self.assertEqual(len(matched), 3)
        metrics = calculate_comparison_metrics(matched, origin_price=6.55)
        self.assertGreater(metrics["MAE"], 0.0)
        self.assertGreater(metrics["RMSE"], 0.0)
        self.assertEqual(metrics["Directional Accuracy"], 100.0)

if __name__ == "__main__":
    unittest.main()
