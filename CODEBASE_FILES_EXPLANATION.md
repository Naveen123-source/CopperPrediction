# Multi-Horizon Copper Price Forecasting System: Complete Codebase & Files Explanation

This document provides a comprehensive, detailed breakdown of **every file** used in the Multi-Horizon Copper Price Forecasting project. It details the purpose, architectural role, key classes/functions, inputs, outputs, mathematical logic, and inter-file dependencies for each component.

---

## 📁 Repository Structure Overview

```text
files_v4/files/
│
├── 🧠 Core Pipeline & Orchestration
│   ├── data_manager.py                 # Data ingestion, causal feature engineering & purged splitting
│   ├── pipeline.py                     # Multi-horizon forecasting execution & SSE streaming engine
│   ├── tuner.py                        # Metric-specific purged TimeSeriesSplit hyperparameter tuner
│   ├── metrics.py                      # 11-metric financial evaluation engine
│   ├── leakage_guard.py                # Zero data leakage static & runtime audit engine
│   └── server.py                       # FastAPI REST backend, SSE streaming & actual upload handler
│
├── 🤖 Machine Learning & Time-Series Models (models/)
│   ├── models/__init__.py              # Model package registry (MODEL_REGISTRY mapping)
│   ├── models/base.py                  # Abstract base class (BaseModel interface)
│   ├── models/tree_models.py           # XGBoost, CatBoost, LightGBM & Random Forest regressors
│   ├── models/stacking.py              # Out-of-fold TimeSeriesSplit Stacking Ensemble with Ridge Meta-Learner
│   ├── models/stage_regression.py      # Two-stage model: Linear Ridge Trend + XGBoost Residual Booster
│   ├── models/time_series_models.py    # Econometric ARIMA & SARIMAX with causal exogenous inputs
│   └── models/lstm_model.py            # Deep LSTM Recurrent Neural Network with 3D sliding sequences
│
├── 📊 Data Ingestion & Generation
│   ├── market_data.csv                 # Primary continuous market dataset (OHLCV + Macro + Physical)
│   ├── download_real_yahoo_data.py     # Live Yahoo Finance data downloader (HG=F, CL=F, DX-Y, ^TNX)
│   └── data_generator.py               # Offline synthetic market data generator with GARCH volatility
│
├── 🖥️ Web Interface & Visualization (static/)
│   ├── static/index.html               # Single-page terminal dashboard, modals & comparison suite
│   ├── static/style.css                # Dark-mode glassmorphic styling, responsive layout & animations
│   └── static/app.js                   # Frontend controller, SSE streaming, Chart.js & upload matcher
│
├── 🧪 Testing, Validation & Diagnostics
│   ├── diagnose_models.py              # Diagnostic script: Non-stationary vs Direct Delta regression
│   ├── verify_full_pipeline.py         # Verification script across all 9 models & continuous ranges
│   ├── validate_api_and_ui.py          # End-to-end API and UI endpoint verification suite
│   ├── test_system.py                  # Unit and integration test suite (features, targets, leakage)
│   ├── test_continuous_api.py          # API test for continuous daily horizon forecasting (Day 1..90)
│   ├── test_comparison_flow.py         # Unit tests for post-forecast actual market data comparison
│   └── test_e2e_forecast_and_upload.py # End-to-end forecast + actual CSV upload and date matching test
│
└── 📖 Architectural & Technical Documentation
    ├── TECHNICAL_KNOWLEDGE_DOCUMENT.md             # In-depth technical architecture and system specifications
    ├── COPPER_FORECASTING_SYSTEM_ARCHITECTURE.md   # Architectural design, data pipeline & methodology
    └── CODEBASE_FILES_EXPLANATION.md               # Complete file-by-file reference guide (this document)
```

---

## 1. Core Pipeline & Orchestration

### 1.1 [`data_manager.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/data_manager.py)
* **Role:** Primary Data Engine, Causal Feature Engineer, and Horizon Splitter.
* **Key Class / Functions:**
  * `DataManager`: Main class managing data loading, feature engineering, summary cards, and dataset extraction.
  * `get_working_day_target_date(start_date, horizon_days)`: Calculates future business calendar target dates by skipping Saturdays and Sundays (Monday–Friday trading days).
  * `load_and_process()`: Ingests CSV, sorts chronologically, resolves column aliases, computes 11 causal features, generates 90 direct delta targets, and drops NaN warmup rows.
  * `get_market_summary()`: Produces real-time snapshot metrics (Open, High, Low, Close, Daily Change, Volume, LME Stock, Crude Oil, DXY, Interest Rate, Basis Spread).
  * `get_dataset_for_horizon(horizon)`: Extracts feature matrix $X$, delta target $y = \text{Close}[t+h] - \text{Close}[t]$, ground-truth target $\text{Close}[t+h]$, origin base prices, and latest row $X_{\text{latest}}$.
  * `split_chronological(X, y, horizon, train_ratio, val_ratio, ...)`: Enforces **Horizon-Aware Purged Chronological Splitting** where the final $h$ rows of training/validation partitions are purged to guarantee zero target realization overlap into future sets.
* **Inputs:** `market_data.csv` (or custom uploaded CSV).
* **Outputs:** Clean supervised dataframes, split matrices ($X_{\text{train}}, y_{\text{train}}, X_{\text{val}}, y_{\text{val}}, X_{\text{test}}, y_{\text{test}}$), market summary dictionaries.

---

### 1.2 [`pipeline.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/pipeline.py)
* **Role:** Asynchronous Multi-Horizon Forecasting Execution & Live Streaming Engine.
* **Key Class / Functions:**
  * `ForecastingPipeline`: Orchestrates experimental loops across $\text{Selected Models} \times \text{Horizons} \times \text{Train/Test Ratios} \times \text{Metrics}$.
  * `run_multi_horizon_forecast(...)`: Runs in a background thread, performs static leakage audits, trains models, performs price reconstruction ($\hat{P}_{t+h} = P_t + \hat{\Delta}_h$), calculates all 11 evaluation metrics, and streams real-time progress callbacks.
  * `cancel_job(job_id)`: Safely cancels running forecasting jobs on user demand.
* **Inputs:** Request parameters (`selected_models`, `selected_metrics`, `selected_horizons`, `selected_ratios`, `auto_tuning`).
* **Outputs:** Formatted result card items, real-time SSE progress events, and cached experiment results.

---

### 1.3 [`tuner.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/tuner.py)
* **Role:** Time-Series Aware, Metric-Specific Hyperparameter Optimization.
* **Key Class / Functions:**
  * `MetricSpecificTuner`: Optimizes hyperparameters targeting the specific metric selected by the user (e.g., minimizing RMSE/MAE or maximizing $R^2$/Directional Accuracy).
  * `PARAM_GRIDS`: Defined search grids for all 9 model types.
  * `tune(...)`: Performs purged `TimeSeriesSplit` cross-validation **strictly within the training partition** ($X_{\text{train}}$), reconstructing prices within each CV fold before computing the target metric score.
* **Inputs:** Model name, horizon $h$, target metric name, training matrices ($X_{\text{train}}, y_{\text{train}}, \text{base\_train}$).
* **Outputs:** Optimal hyperparameter dictionary `best_params`.

---

### 1.4 [`metrics.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/metrics.py)
* **Role:** Mathematical Evaluation Engine.
* **Key Functions:**
  * `calculate_mae(y_true, y_pred)`: Mean Absolute Error ($/lb).
  * `calculate_rmse(y_true, y_pred)`: Root Mean Squared Error ($/lb).
  * `calculate_mape(y_true, y_pred)`: Mean Absolute Percentage Error (%).
  * `calculate_smape(y_true, y_pred)`: Symmetric MAPE (%).
  * `calculate_r2(y_true, y_pred)`: Coefficient of Determination ($R^2$).
  * `calculate_mean_error(y_true, y_pred)`: Prediction Bias ($\text{Pred} - \text{True}$).
  * `calculate_directional_accuracy(y_true, y_pred, y_base)`: Percentage of correct market direction predictions relative to price at origin $t$.
  * `calculate_up_accuracy(y_true, y_pred, y_base)`: Accuracy strictly during market upward moves.
  * `calculate_down_accuracy(y_true, y_pred, y_base)`: Accuracy strictly during market downward moves.
  * `calculate_max_abs_error(y_true, y_pred)`: Maximum Absolute Error ($/lb).
  * `calculate_error_std(y_true, y_pred)`: Standard deviation of prediction residuals.
  * `calculate_all_metrics(y_true, y_pred, y_base)`: Computes all 11 metrics in a single unified dictionary.
* **Inputs:** Ground truth price array $y_{\text{true}}$, predicted price array $y_{\text{pred}}$, base origin price array $y_{\text{base}}$.
* **Outputs:** Dictionary of 11 evaluated financial metrics.

---

### 1.5 [`leakage_guard.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/leakage_guard.py)
* **Role:** Static & Runtime Zero Data Leakage Audit Engine.
* **Key Class / Functions:**
  * `LeakageGuard.audit_splits(...)`: Verifies chronological timestamp ordering ($\text{Train} < \text{Val} < \text{Test}$) and target realization boundaries ($\text{Max Train Target Date} \le \text{Min Val Date}$ and $\text{Max Val Target Date} \le \text{Min Test Date}$).
  * `LeakageGuard.audit_features(...)`: Verifies all lag, return, and rolling indicators are strictly causal ($t-1 \to t-10$) without lookahead bias.
  * `LeakageGuard.audit_scaler(...)`: Confirms scalers are fitted solely on training partitions.
* **Inputs:** Partition date vectors, feature dataframes, scaler state flags.
* **Outputs:** Audit status reports (`PASS`/`FAIL`) with detailed diagnostic logs.

---

### 1.6 [`server.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/server.py)
* **Role:** FastAPI REST API Server, SSE Broadcaster, and Static File Host.
* **Key Endpoints:**
  * `GET /api/market-summary`: Returns the latest 12 market indicator metrics for dashboard cards.
  * `GET /api/historical-data?limit=250`: Returns recent historical OHLCV and macroeconomic time series for charts.
  * `GET /api/config`: Returns available models, 11 metrics, fixed horizons, continuous ranges, and split ratios.
  * `POST /api/forecast/run`: Spawns asynchronous multi-horizon forecast execution in a dedicated thread.
  * `GET /api/forecast/status/{job_id}`: Polling endpoint for job status and progress.
  * `GET /api/forecast/stream/{job_id}`: Server-Sent Events (SSE) live progress stream.
  * `GET /api/forecast/results/{job_id}`: Returns all formatted forecast result cards and metrics.
  * `POST /api/forecast/cancel/{job_id}`: Cancels a running forecasting job.
  * `POST /api/forecast/upload-actual`: Parses uploaded actual market CSV/Excel files for post-forecast ground-truth comparison (never used for training/tuning).
  * `POST /api/data/upload`: Allows uploading custom historical market CSVs.
  * Mount `/`: Serves static web assets (`static/index.html`, `static/style.css`, `static/app.js`).
* **Inputs:** HTTP requests, JSON payloads, multipart file uploads.
* **Outputs:** JSON responses, SSE event streams, static web files.

---

## 2. Machine Learning & Time-Series Models (`models/`)

### 2.1 [`models/__init__.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/__init__.py)
* **Role:** Models package initializer and central model registry.
* **Key Content:** Exposes `MODEL_REGISTRY` mapping string model names to their respective Python classes:
  * `"XGBoost"`, `"CatBoost"`, `"LightGBM"`, `"RandomForest"`, `"Stacking Ensemble"`, `"Stage Regression"`, `"ARIMA"`, `"SARIMAX"`, `"LSTM"`.

---

### 2.2 [`models/base.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/base.py)
* **Role:** Abstract Base Class defining standard regressor interface.
* **Key Class / Methods:**
  * `BaseModel(ABC)`: Abstract class requiring `fit(X_train, y_train)` and `predict(X)`.
  * `get_params()`, `set_params(**params)`: Manages model hyperparameters consistently across all regressors.

---

### 2.3 [`models/tree_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/tree_models.py)
* **Role:** Tree-based ensemble regressors.
* **Key Classes:**
  * `XGBoostModel`: Extreme Gradient Boosting with tree regularization and multi-threading.
  * `CatBoostModel`: Categorical Gradient Boosting using symmetric oblivious trees and ordered boosting.
  * `LightGBMModel`: High-speed Light Gradient Boosting with histogram binning and leaf-wise tree splitting.
  * `RandomForestModel`: Bagged random decision forest ensemble averaging multiple de-correlated trees.
* **Training & Inference:** Fits directly on $X_{\text{train}}$ to predict direct horizon price delta $\hat{\Delta}_h$.

---

### 2.4 [`models/stacking.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/stacking.py)
* **Role:** Leakage-Free Multi-Model Stacking Ensemble.
* **Key Class / Logic:**
  * `StackingEnsembleModel`: Combines base learners (XGBoost, CatBoost, LightGBM, Random Forest) through a secondary meta-model.
  * **Zero Leakage OOF Strategy:** Uses strictly chronological `TimeSeriesSplit` cross-validation on $X_{\text{train}}$ with purged horizon boundaries to generate out-of-fold (OOF) predictions.
  * **Meta-Model:** Fits a non-negative Regularized Ridge Meta-Regressor on the OOF prediction matrix to learn optimal dynamic model weights.
  * **Final Fit:** Re-trains all 4 base models on the entire $X_{\text{train}}$ for test/future inference.

---

### 2.5 [`models/stage_regression.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/stage_regression.py)
* **Role:** Two-Stage Hybrid Macro Trend & Nonlinear Residual Regressor.
* **Key Class / Logic:**
  * `StageRegressionModel`: Decomposes direct multi-horizon forecasting into two sequential stages:
    * **Stage 1 (Macro Trend):** Fits a `StandardScaler` + `Ridge` linear regression on macroeconomic exogenous variables (Crude Oil, DXY, Interest Rate, LME Stocks, Basis Spread) to capture linear macro drift.
    * **Stage 2 (Nonlinear Residuals):** Calculates Stage 1 residuals ($\epsilon = y - \hat{y}_{\text{Stage1}}$) and fits an `XGBRegressor` on the residual space to capture nonlinear market micro-dynamics.
  * **Combined Inference:** $\hat{y} = \hat{y}_{\text{Stage1}}(\text{scaled } X) + \hat{y}_{\text{Stage2}}(X)$.

---

### 2.6 [`models/time_series_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/time_series_models.py)
* **Role:** Classical & Exogenous Econometric Time-Series Regressors.
* **Key Classes:**
  * `ARIMAForecastModel`: AutoRegressive Integrated Moving Average fitted on the series with an out-of-sample regularized Ridge fallback blend to guarantee numerical stability across extended horizons.
  * `SARIMAXForecastModel`: Seasonal ARIMAX with regularized ElasticNet regression over standardized causal macroeconomic exogenous features (Crude Oil, DXY, 10Y Yield, LME Stocks, Basis Spread).

---

### 2.7 [`models/lstm_model.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/lstm_model.py)
* **Role:** Deep Recurrent Neural Network with 3D Sequence Windows.
* **Key Class / Logic:**
  * `LSTMForecastModel`: Implements TensorFlow/Keras Long Short-Term Memory architecture.
  * **Sequence Transformation:** Converts 2D feature matrix into 3D sliding sequence arrays $[N, \text{window\_size}, \text{features}]$ without shuffling to preserve chronological ordering.
  * **Normalization Isolation:** Fits `MinMaxScaler` strictly on $X_{\text{train}}$ and $y_{\text{train}}$, applying inverse transforms post-inference.
  * **Network Structure:** Input Layer $\to$ LSTM Layer (32 units) $\to$ Dropout (0.1) $\to$ Dense (16 units, ReLU) $\to$ Dense (1 unit linear output).

---

## 3. Data Ingestion & Generation

### 3.1 [`market_data.csv`](file:///c:/COPTech/Prediction_Codes/files_v4/files/market_data.csv)
* **Role:** Primary Historical Market Dataset.
* **Structure:** Daily time-series records containing:
  * `Date`: Trading day timestamp ($YYYY-MM-DD$).
  * `Copper_Open`, `Copper_High`, `Copper_Low`, `Copper_Close`, `Copper_Volume`: COMEX Copper continuous futures ($HG=F$).
  * `Crude_Oil`: WTI Crude Oil continuous futures ($CL=F$, $/barrel).
  * `DXY_Index`: US Dollar Index ($DX-Y.NYB$).
  * `Interest_Rate`: US 10-Year Treasury Yield ($^TNX$, %).
  * `LME_Stocks`: London Metal Exchange Copper warehouse stocks (Metric Tons).
  * `Basis_Spread_3M_Cash`: LME 3-Month minus Cash settlement spread ($/t).

---

### 3.2 [`download_real_yahoo_data.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/download_real_yahoo_data.py)
* **Role:** Real-World Data Downloader & Synchronizer.
* **Key Functions:**
  * `fetch_and_build_market_csv(filepath, period)`: Connects to Yahoo Finance via `yfinance` to download real historical daily bars for `HG=F`, `CL=F`, `DX-Y.NYB`, and `^TNX`.
  * Merges feeds by calendar date, applies forward/backward fills for missing holiday dates, generates realistic physical inventory and basis spread trajectories, and exports `market_data.csv`.

---

### 3.3 [`data_generator.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/data_generator.py)
* **Role:** Offline Market Dataset Generator & Fallback Simulator.
* **Key Functions:**
  * `generate_market_dataset(filepath)`: Attempts live Yahoo Finance fetch; if offline or unavailable, generates synthetic market time-series using GARCH(1,1) volatility clustering, cyclical commodity trends, and inverse macroeconomic correlations.

---

## 4. Web Interface & Dashboard (`static/`)

### 4.1 [`static/index.html`](file:///c:/COPTech/Prediction_Codes/files_v4/files/static/index.html)
* **Role:** Complete Single-Page Application (SPA) HTML Layout.
* **Key Sections:**
  * **Top Header & Status Bar:** System branding, active dataset indicator, and zero-leakage badge.
  * **Market Overview Grid (12 Cards):** Live Yahoo Finance-style metrics (Open, High, Low, Close, Change, %, Volume, Stocks, Oil, DXY, 10Y Yield, Spread).
  * **Interactive Configuration Terminal:**
    * Model selection dropdown with "Select All" / "Clear All" toggles.
    * Metric selection dropdown (11 metrics).
    * Forecast mode switch: **Fixed Horizon Chips** (1, 7, 15, 30, 60, 90 Days) vs **Continuous Horizon Ranges** (1–7, 1–15, 1–30, 1–60, 1–90 Days).
    * Split Ratio selector (80:20 standard, 70:30, 75:25, 60:40, 85:15).
    * Hyperparameter Auto-Tuning toggle.
    * Action buttons: "Run Multi-Horizon Forecast" and "Cancel Run".
  * **Live Progress Strip:** Animated progress bar, experiment counter, current step indicator, elapsed time.
  * **Single Global Actual Market Data Upload Toolbar:** Upload CSV/Excel button, date range badges, and "Compare Actual vs Forecast" control.
  * **Dynamic Results Grid & Comparison Matrix:** Generated forecast cards, metric badges, price changes, target dates, and detailed breakdown tables.
  * **Detailed Card Expansion Modal Dialog:** High-resolution Chart.js price trajectory charts, full 11-metric performance tables, train/val/test split audits, and historical sample points.

---

### 4.2 [`static/style.css`](file:///c:/COPTech/Prediction_Codes/files_v4/files/static/style.css)
* **Role:** Modern Financial Terminal Styling & Design System.
* **Key Design Features:**
  * **Theme:** Deep dark-mode palette (`#0a0e17`, `#111827`, `#1f2937`) with neon blue (`#38bdf8`), emerald green (`#10b981`), amber (`#f59e0b`), and rose red (`#f43f5e`) accents.
  * **Glassmorphism:** Frosted translucent panels with subtle borders, blurs, and shadows.
  * **Typography:** Clean tabular-num monospace and modern sans-serif fonts for financial data alignment.
  * **Responsive Grid:** Adaptive CSS grid and flex layouts for seamless desktop and tablet viewing.
  * **Animations:** Smooth progress animations, hover state transitions, pulse badges, and modal fade-ins.

---

### 4.3 [`static/app.js`](file:///c:/COPTech/Prediction_Codes/files_v4/files/static/app.js)
* **Role:** Client-Side Application Controller, SSE Handler & Chart Visualizer.
* **Key Functions & State Management:**
  * `initApp()`: Fetches initial market summary and configuration from backend on page load.
  * `handleForecastRun()`: Validates inputs, sends POST request to `/api/forecast/run`, and initializes live SSE stream.
  * `listenToProgressStream(jobId)`: Connects to `/api/forecast/stream/{jobId}` via `EventSource` to render live progress and status.
  * `renderResultsCards(cards)`: Dynamically generates cards for all completed experiments with color-coded price movements and audit badges.
  * `handleActualDataUpload(file)`: Sends uploaded CSV/Excel to `/api/forecast/upload-actual`, parses ground-truth prices, and binds them to the global comparison state.
  * `updateCardsWithActualComparison()`: Matches forecast target dates with uploaded actual market dates, computes comparison metrics (MAE, RMSE, MAPE, Directional Accuracy), and renders side-by-side badges.
  * `openCardModal(cardId)`: Launches high-resolution modal dialog with Chart.js line plots comparing Predicted vs Test vs Actual trajectories.

---

## 5. Testing, Validation & Diagnostic Scripts

### 5.1 [`diagnose_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/diagnose_models.py)
* **Role:** Mathematical Diagnostic Script on Market Stationarity.
* **Logic:** Evaluates all 9 models on 7-day horizon forecasting under two paradigms:
  1. *Experiment A (Non-Stationary):* Directly predicting raw closing price level $y = \text{Close}[t+h]$.
  2. *Experiment B (Stationary Direct Delta):* Predicting relative price delta $\Delta_h = \text{Close}[t+h] - \text{Close}[t]$ and reconstructing price.
* **Conclusion:** Proves that stationary delta formulation eliminates regime drift, avoids out-of-sample mean collapse, and achieves superior $R^2$ and MAE.

---

### 5.2 [`verify_full_pipeline.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/verify_full_pipeline.py)
* **Role:** Full End-to-End Pipeline Verification Script.
* **Logic:** Executes automated API tests against the running server for:
  1. All 9 models across key fixed horizons ($1, 7, 15, 30, 60, 90$ Days) with 4 metrics.
  2. Continuous day-by-day range ($1 \to 7$ Days).
  3. Verifies zero data leakage status (`PASS`) and price sanity across all generated cards.

---

### 5.3 [`validate_api_and_ui.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/validate_api_and_ui.py)
* **Role:** Automated API & UI Endpoint Verification.
* **Logic:** Tests HTTP response codes and payload structures for UI landing page (`/`), market summary (`/api/market-summary`), historical data (`/api/historical-data`), configuration (`/api/config`), and multi-model forecast execution.

---

### 5.4 [`test_system.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/test_system.py)
* **Role:** Comprehensive Unit & Integration Test Suite (`unittest`).
* **Test Cases:**
  * `test_causal_features_integrity`: Verifies all 11 features strictly use historical lags.
  * `test_direct_multi_horizon_targets`: Verifies delta target construction across horizons.
  * `test_chronological_splits_leakage`: Verifies train/val/test boundary timestamps and zero overlap.
  * `test_all_11_metrics`: Verifies mathematical correctness of all evaluation functions.
  * `test_models_fit_and_predict`: Tests training and prediction for all 9 regressors.

---

### 5.5 [`test_continuous_api.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/test_continuous_api.py)
* **Role:** Continuous Horizon API Test.
* **Logic:** Sends continuous sequence requests ($1 \to 7$ Days) to `/api/forecast/run`, polls progress, and asserts that 28 distinct direct horizon forecast cards are generated with zero data leakage.

---

### 5.6 [`test_comparison_flow.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/test_comparison_flow.py)
* **Role:** Post-Forecast Comparison Unit Tests (`unittest`).
* **Logic:** Validates the calculation of comparison metrics (MAE, RMSE, MAPE, sMAPE, $R^2$, Bias, Directional Accuracy) between predicted price sequences and uploaded actual market prices under exact-match, constant-offset, and inverse scenarios.

---

### 5.7 [`test_e2e_forecast_and_upload.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/test_e2e_forecast_and_upload.py)
* **Role:** End-to-End Integration Test for Forecast + Actual Market Data Upload.
* **Logic:** Runs a continuous 7-day forecast, extracts generated target dates, generates a realistic partial actual market CSV, uploads it to `/api/forecast/upload-actual`, and validates exact date-matching and metric evaluation.

---

## 6. Architecture & Technical Documentation

### 6.1 [`TECHNICAL_KNOWLEDGE_DOCUMENT.md`](file:///c:/COPTech/Prediction_Codes/files_v4/files/TECHNICAL_KNOWLEDGE_DOCUMENT.md)
* **Role:** Comprehensive Master Technical Knowledge Document (67+ KB).
* **Contents:** Executive summary, economic rationale, complete 11-feature math specifications, direct delta target equations, 9 model architectures, purged chronological splitting math, step-by-step price reconstruction examples, zero-leakage guarantees, and full API/UI reference.

---

### 6.2 [`COPPER_FORECASTING_SYSTEM_ARCHITECTURE.md`](file:///c:/COPTech/Prediction_Codes/files_v4/files/COPPER_FORECASTING_SYSTEM_ARCHITECTURE.md)
* **Role:** System Architecture, Data Pipeline & Methodology Specification.
* **Contents:** Market indicators table, economic rationale for macroeconomic variables, 11 causal stationary features, direct delta formulation, 9 model paradigms, weekend-skipping trading day logic, and purged splitting boundaries.

---

## 7. Complete File Interaction & Data Flow Map

```text
                                  ┌───────────────────────────┐
                                  │ download_real_yahoo_data  │
                                  │    or data_generator      │
                                  └─────────────┬─────────────┘
                                                │ creates
                                                ▼
                                      ┌──────────────────┐
                                      │ market_data.csv  │
                                      └─────────┬────────┘
                                                │ loaded by
                                                ▼
                                      ┌──────────────────┐
                                      │ data_manager.py  │
                                      └─────────┬────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
    ┌──────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
    │     leakage_guard.py     │   │        tuner.py          │   │      models/*.py         │
    │ (Static & Runtime Audit) │   │ (Metric-Specific Tuning) │   │ (9 Specialized Regressors)│
    └────────────┬─────────────┘   └────────────┬─────────────┘   └────────────┬─────────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                │ orchestrated by
                                                ▼
                                      ┌──────────────────┐
                                      │   pipeline.py    │ ◄─── metrics.py (11 Metrics)
                                      └─────────┬────────┘
                                                │ runs within
                                                ▼
                                      ┌──────────────────┐
                                      │    server.py     │ ◄─── REST & SSE API
                                      └─────────┬────────┘
                                                │ serves & interacts with
                                                ▼
                                  ┌───────────────────────────┐
                                  │ static/ (index.html,      │
                                  │         style.css, app.js)│
                                  └───────────────────────────┘
```

---

*Document Generated: 2026-09-02 | Multi-Horizon Copper Forecasting System | Files Reference Guide*
