# Copper Price Forecasting System: Architecture, Data Pipeline, Models & Methodology

This document provides a comprehensive technical overview of the **Multi-Horizon Copper Price Forecasting System**, covering data ingestion, economic rationale, causal feature engineering, direct target formulation, machine learning architectures, purged chronological splitting, and the step-by-step mathematical forecasting workflow.

---

## Table of Contents
1. [Data Sources & Market Indicators](#1-data-sources--market-indicators)
2. [Economic Rationale for Selected Variables](#2-economic-rationale-for-selected-variables)
3. [X Features – 11 Causal, Stationary & Relative Inputs](#3-x-features--11-causal-stationary--relative-inputs)
4. [Y Target – Direct Multi-Horizon Delta Formulation](#4-y-target--direct-multi-horizon-delta-formulation)
5. [The 9 Forecasting Models & Algorithmic Paradigm](#5-the-9-forecasting-models--algorithmic-paradigm)
6. [Horizon-Aware Purged Chronological Splitting](#6-horizon-aware-purged-chronological-splitting)
7. [Step-by-Step Forecasting & Price Reconstruction (With Example)](#7-step-by-step-forecasting--price-reconstruction-with-example)
8. [Weekend-Skipping Trading Day Logic](#8-weekend-skipping-trading-day-logic)
9. [Zero Data Leakage Guarantees](#9-zero-data-leakage-guarantees)

---

## 1. Data Sources & Market Indicators

The system compiles continuous daily financial time-series through [`download_real_yahoo_data.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/download_real_yahoo_data.py) and [`data_manager.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/data_manager.py), combining official Yahoo Finance data (`yfinance`) with physical inventory and term-structure indicators stored in [`market_data.csv`](file:///c:/COPTech/Prediction_Codes/files_v4/files/market_data.csv).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 RAW MARKET TIME-SERIES                                 │
├────────────────────┬───────────────────────────────────────┬───────────────────────────┤
│ Ticker / Variable  │ Description                           │ Sampling Frequency        │
├────────────────────┼───────────────────────────────────────┼───────────────────────────┤
│ HG=F               │ COMEX Copper Continuous Futures       │ Daily Trading Bars (OHLCV)│
│ CL=F               │ WTI Crude Oil Continuous Futures      │ Daily Close ($/bbl)       │
│ DX-Y.NYB           │ US Dollar Index (DXY)                 │ Daily Close Index Level   │
│ ^TNX               │ US 10-Year Treasury Constant Yield    │ Daily Yield (%)           │
│ LME_Stocks         │ London Metal Exchange Warehouse Stock │ Daily Physical Tonnes (MT)│
│ Basis_Spread       │ 3-Month Futures vs. Cash Basis Spread │ Daily Spread ($/MT)       │
└────────────────────┴───────────────────────────────────────┴───────────────────────────┘
```

---

## 2. Economic Rationale for Selected Variables

| Variable | Market Role | Fundamental Economic & Forecasting Rationale |
| :--- | :--- | :--- |
| **`Copper_Close`** | Primary Target | Base commodity price (USD per pound, $/lb). Reflects physical spot equilibrium between global industrial demand and mine supply. |
| **`Crude_Oil` (WTI)** | Energy & Industrial Cost | Copper extraction, smelting, and refining are highly energy-intensive. Oil price fluctuations directly alter mining operational costs and serve as a proxy for global macroeconomic velocity. |
| **`DXY_Index` (USD)** | Currency Valuation Factor | Copper is globally traded in US Dollars. An appreciating USD increases the cost of copper for foreign buyers (China, Europe), dampening global consumption (strong historical inverse relationship). |
| **`Interest_Rate` (10Y Yield)** | Cost of Capital & Discount Rate | Reflects institutional inflation expectations, borrowing costs, and holding/financing costs for physical commodity warehouse inventories. |
| **`LME_Stocks`** | Physical Supply/Demand Balance | London Metal Exchange registered warehouse inventory levels. Drawdowns indicate immediate spot shortages; inventory builds signal oversupply. |
| **`Basis_Spread_3M_Cash`** | Market Term Structure | The spread between 3-Month futures and Cash settlement prices: <br>• **Backwardation (Spread > 0):** Cash at a premium $\to$ immediate physical shortage (Bullish).<br>• **Contango (Spread < 0):** Futures at a premium $\to$ abundant spot supply (Bearish). |

---

## 3. X Features – 11 Causal, Stationary & Relative Inputs

To guarantee zero lookahead bias and model stationarity across market regimes, **every feature is strictly backward-looking ($t-1$ to $t-11$)**:

```text
       t-10          t-3    t-2    t-1     t (Origin)       t+h (Target Date)
────────┼─────────────┼──────┼──────┼──────┼────────────────────────┼────────►
        │             │      │      │      │                        │
        └─────────────┴──────┴──────┴──────┘                        │
           Historical Feature Window (X_t)                          ▼
                                                        Target Price: Close[t+h]
                                                        Target Delta: Close[t+h] - Close[t]
```

### Feature Specification Table ([`data_manager.py:L114-L146`](file:///c:/COPTech/Prediction_Codes/files_v4/files/data_manager.py#L114-L146))

| # | Feature Column Name | Mathematical Formula | Historical Window | Economic / Technical Signal |
| :-: | :--- | :--- | :-: | :--- |
| **1** | **Copper Price Lag 1 Return** | $\frac{\text{Close}_{t-1} - \text{Close}_{t-2}}{\text{Close}_{t-2} + \epsilon}$ | $t-2 \to t-1$ | Prior-day market sentiment and immediate return momentum. |
| **2** | **Copper Price Lag 3 Return** | $\frac{\text{Close}_{t-1} - \text{Close}_{t-3}}{\text{Close}_{t-3} + \epsilon}$ | $t-3 \to t-1$ | Multi-day short-term trend direction. |
| **3** | **Copper Price Lag 10 Return** | $\frac{\text{Close}_{t-1} - \text{Close}_{t-10}}{\text{Close}_{t-10} + \epsilon}$ | $t-10 \to t-1$ | Bi-weekly price momentum trajectory. |
| **4** | **Copper Rolling Mean Relative** | $\frac{\mu_{10}(\text{Close}_{t-1}) - \text{Close}_{t-1}}{\text{Close}_{t-1} + \epsilon}$ | $t-10 \to t-1$ | Mean-reversion indicator (percentage distance from 10-day moving average). |
| **5** | **Copper Momentum Return** | $\frac{\text{Close}_{t-1} - \text{Close}_{t-10}}{\text{Close}_{t-10} + \epsilon}$ | $t-10 \to t-1$ | Velocity of price acceleration over the trailing 10 sessions. |
| **6** | **Crude Oil (WTI) Return** | $\text{pct\_change}(\text{Crude\_Oil})_{t-1}$ | $t-2 \to t-1$ | Inter-commodity cost transmission and energy pressure. |
| **7** | **3M vs Cash Basis Spread** | $\frac{\text{Basis\_Spread}_{t-1}}{\text{Close}_{t-1} + \epsilon}$ | $t-1$ | Normalized physical term structure pressure. |
| **8** | **LME Stocks Change** | $\text{pct\_change}(\text{LME\_Stocks})_{t-1}$ | $t-2 \to t-1$ | Daily physical inventory accumulation or draw rate. |
| **9** | **US Dollar Index (DXY) Return** | $\text{pct\_change}(\text{DXY})_{t-1}$ | $t-2 \to t-1$ | Foreign exchange purchasing power impact. |
| **10** | **Interest Rate Change** | $\Delta(\text{Interest\_Rate})_{t-1}$ | $t-2 \to t-1$ | Shift in macroeconomic discount rates and inventory carrying costs. |
| **11** | **Realized Volatility** | $\sigma_{10}\big(\text{pct\_change}(\text{Close})_{t-1}\big)$ | $t-11 \to t-1$ | 10-day market uncertainty and risk regime proxy. |

---

## 4. Y Target – Direct Multi-Horizon Delta Formulation

### Why Direct Delta Forecasting?
Predicting raw closing prices level-by-level ($\text{Close}[t+h]$) suffers from non-stationarity, unit roots, and regime drift. Predicting percentage returns or deltas guarantees stationary modeling:

### 1. Training Target ($\text{Target\_Delta}_h[t]$)
For each direct forecast horizon $h \in \{1, 2, \dots, 90\}$:
$$\text{Target\_Delta}_h[t] = \text{Copper\_Close}[t+h] - \text{Copper\_Close}[t]$$
The model learns to estimate the **price delta** over exactly $h$ forward working days.

### 2. Ground-Truth Evaluation Target ($\text{Target}_h[t]$)
$$\text{Target}_h[t] = \text{Copper\_Close}[t+h]$$
The unshifted absolute price level observed at $t+h$, used exclusively post-inference to compute error metrics (RMSE, MAE, MAPE, $R^2$, Directional Accuracy).

---

## 5. The 9 Forecasting Models & Algorithmic Paradigm

```
                          ┌───────────────────────────────────────┐
                          │         9 FORECASTING MODELS          │
                          └───────────────────┬───────────────────┘
         ┌────────────────────────────────────┼────────────────────────────────────┐
         ▼                                    ▼                                    ▼
┌─────────────────────────┐          ┌─────────────────────────┐          ┌─────────────────────────┐
│     Tree Ensembles      │          │    Two-Stage & Meta     │          │  Time-Series & Deep ML  │
├─────────────────────────┤          ├─────────────────────────┤          ├─────────────────────────┤
│ 1. XGBoost              │          │ 5. Stacking Ensemble    │          │ 7. ARIMA                │
│ 2. CatBoost             │          │ 6. Stage Regression     │          │ 8. SARIMAX              │
│ 3. LightGBM             │          │                         │          │ 9. LSTM Neural Network  │
│ 4. RandomForest         │          │                         │          │                         │
└─────────────────────────┘          └─────────────────────────┘          └─────────────────────────┘
```

| Model Name | Code Reference | Core Algorithmic Architecture | Role in Forecasting Pipeline |
| :--- | :--- | :--- | :--- |
| **1. XGBoost** | [`models/tree_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/tree_models.py#L10) | Gradient Boosted Decision Trees with $L_1/L_2$ regularization and column subsampling. | Captures complex non-linear feature interactions and macro thresholds. |
| **2. CatBoost** | [`models/tree_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/tree_models.py#L39) | Oblivious (symmetric) decision trees with ordered boosting. | Prevents target leakage and provides robust generalization on noisy financial returns. |
| **3. LightGBM** | [`models/tree_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/tree_models.py#L67) | Histogram-based Gradient Boosting with leaf-wise tree growth. | High-speed training and deep pattern extraction across 90 separate horizon models. |
| **4. Random Forest** | [`models/tree_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/tree_models.py#L98) | Bootstrap Aggregating (Bagging) of unconstrained regression trees. | Minimizes prediction variance and stabilizes noisy daily market fluctuations. |
| **5. Stacking Ensemble** | [`models/stacking.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/stacking.py#L17) | Multi-model meta-learner combining OOF predictions from XGBoost, CatBoost, LightGBM, and RF. | Uses a regularized non-negative Ridge meta-regressor to blend distinct model strengths. |
| **6. Stage Regression** | [`models/stage_regression.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/stage_regression.py#L15) | **Two-stage hybrid model:**<br>• Stage 1: Ridge linear regression on scaled macro drivers.<br>• Stage 2: XGBoost fitted on Stage 1 residuals. | Decomposes macro linear trends from non-linear residual market volatility. |
| **7. ARIMA** | [`models/time_series_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/time_series_models.py#L16) | Autoregressive Integrated Moving Average $(p, d, q)$ with Ridge fallback. | Models historical price autocorrelation and cyclical momentum patterns. |
| **8. SARIMAX** | [`models/time_series_models.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/time_series_models.py#L75) | Regularized state-space model integrating causal exogenous variables ($X$). | Evaluates price response conditional on external macro shifts (DXY, Oil, Yields). |
| **9. LSTM** | [`models/lstm_model.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/lstm_model.py#L13) | Long Short-Term Memory Deep Recurrent Neural Network over a 10-day sliding window. | Captures sequential time-dependencies and non-linear memory effects across time. |

---

## 6. Horizon-Aware Purged Chronological Splitting

To eliminate **target overlap leakage across partition boundaries**, the system uses **Purged Chronological Splitting** ([`data_manager.py:L234-L290`](file:///c:/COPTech/Prediction_Codes/files_v4/files/data_manager.py#L234-L290)):

```text
 0                      Train Partition                        Val Partition          Test Partition
┌───────────────────────────────────────────────┬──────┐   ┌────────────────────┬──────┐   ┌────────────────┐
│   X_train  (Features available at t)          │Purge │   │      X_val         │Purge │   │     X_test     │
│   y_train  (Target: Close[t+h] - Close[t])    │Gap(h)│   │                    │Gap(h)│   │                │
└───────────────────────────────────────────────┴──────┘   └────────────────────┴──────┘   └────────────────┘
                                                ▲          ▲                    ▲          ▲
                                                │          │                    │          │
                       Latest Train Target Date ┴──────────┘                    │          │
                       (Realized BEFORE Validation Starts)                      │          │
                                                Latest Val Target Date ─────────┴──────────┘
                                                (Realized BEFORE Testing Starts)
```

### Purging Invariant
For any horizon $h$:
- The training slice trims the last $h$ rows: $\text{Train\_End} = \text{Train\_Size} - h$.
- Target realization date of the last training observation ($\text{Date}[i + h]$) is guaranteed to fall **before** validation starts.
- [`LeakageGuard.audit_splits`](file:///c:/COPTech/Prediction_Codes/files_v4/files/leakage_guard.py#L11-L60) validates at runtime:
  $$\text{Target\_Date}(\max(\text{Date}_{\text{train}}), h) \le \min(\text{Date}_{\text{val}}) < \text{Target\_Date}(\max(\text{Date}_{\text{val}}), h) \le \min(\text{Date}_{\text{test}})$$

---

## 7. Step-by-Step Forecasting & Price Reconstruction (With Example)

### Concrete Walkthrough

```text
Forecast Origin Date (t)   : Wednesday, 2026-06-03
Baseline Session Price (P0): $6.4810 / lb
```

```
Step 1: Feature Extraction at Origin (t)
        Extract 11 causal features X_latest from market close on 2026-06-03.
                         │
                         ▼
Step 2: Model Prediction (Delta Regression)
        Model predicts direct price delta: \widehat{\Delta}_h = model.predict(X_latest)
        • Horizon 1 Day  (h=1) : \widehat{\Delta}_1  = -$0.0202
        • Horizon 7 Days (h=7) : \widehat{\Delta}_7  = -$0.0393
        • Horizon 30 Days(h=30): \widehat{\Delta}_30 = -$0.2246
                         │
                         ▼
Step 3: Price Reconstruction (Absolute Level)
        \widehat{\text{Predicted\_Close}}[t+h] = \text{Base\_Price}[t] + \widehat{\Delta}_h
        • 1 Day Forecast : $6.4810 + (-$0.0202) = $6.4608 / lb
        • 7 Day Forecast : $6.4810 + (-$0.0393) = $6.4417 / lb
        • 30 Day Forecast: $6.4810 + (-$0.2246) = $6.2564 / lb
                         │
                         ▼
Step 4: Target Date Assignment (Working-Day Calendar)
        Skip Saturdays and Sundays to find the exact trading date for t+h.
        • 1 Day  -> Thursday,  2026-06-04 (Working Day #1)
        • 7 Days -> Friday,    2026-06-12 (Working Day #7, Weekend Skipped)
        • 30 Days-> Wednesday, 2026-07-15 (Working Day #30)
```

### Result Cards Generated

| Horizon | Origin Date | Origin Price | Target Date | Predicted Price | Price Change ($ / %) | Leakage Audit |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1 Day** | `2026-06-03` | $\$6.4810$ | **`2026-06-04` (Thu)** | **`$6.4608`** | $-\$0.0202\text{ }(-0.31\%)$ | **`PASS`** |
| **7 Days** | `2026-06-03` | $\$6.4810$ | **`2026-06-12` (Fri)** | **`$6.4417`** | $-\$0.0393\text{ }(-0.61\%)$ | **`PASS`** |
| **30 Days** | `2026-06-03` | $\$6.4810$ | **`2026-07-15` (Wed)** | **`$6.2564`** | $-\$0.2246\text{ }(-3.47\%)$ | **`PASS`** |

---

## 8. Weekend-Skipping Trading Day Logic

In financial markets, trading occurs strictly Monday through Friday. [`get_working_day_target_date`](file:///c:/COPTech/Prediction_Codes/files_v4/files/data_manager.py#L30-L42) enforces this:

```python
def get_working_day_target_date(start_date, horizon_days: int) -> str:
    current = pd.to_datetime(start_date)
    working_days_count = 0
    while working_days_count < horizon_days:
        current += pd.Timedelta(days=1)
        if current.weekday() < 5:  # 0=Monday, ..., 4=Friday (excludes Saturday 5 and Sunday 6)
            working_days_count += 1
    return current.strftime("%Y-%m-%d")
```

### Example (Starting Wednesday 2026-06-03)
- **Day 1** $\to$ Thursday `2026-06-04` (Predict)
- **Day 2** $\to$ Friday `2026-06-05` (Predict)
- *Saturday `2026-06-06`* $\to$ **[SKIPPED]**
- *Sunday `2026-06-07`* $\to$ **[SKIPPED]**
- **Day 3** $\to$ Monday `2026-06-08` (Predict)
- **Day 4** $\to$ Tuesday `2026-06-09` (Predict)
- **Day 5** $\to$ Wednesday `2026-06-10` (Predict)
- **Day 6** $\to$ Thursday `2026-06-11` (Predict)
- **Day 7** $\to$ Friday `2026-06-12` (Predict)

---

## 9. Zero Data Leakage Guarantees

1. **Stationary Causal Features:** No feature uses information past time $t-1$ (all lags explicitly shifted).
2. **Purged Boundary Isolation:** Training labels never overlap with validation or testing evaluation periods.
3. **Dedicated Scalers:** Preprocessors (`StandardScaler`, `MinMaxScaler`) are fitted exclusively on `X_train` during `fit()` and applied via `.transform()` during `predict()`.
4. **Purged Cross-Validation:** Internal `TimeSeriesSplit` in [`tuner.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/tuner.py) and [`models/stacking.py`](file:///c:/COPTech/Prediction_Codes/files_v4/files/models/stacking.py) applies an $h$-sample embargo gap between folds.
5. **Post-Inference Evaluation:** Actual market data and ground-truth values are strictly accessed after predictions are finalized to compute error metrics.
