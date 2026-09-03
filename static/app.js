/**
 * Multi-Horizon Copper Forecasting Terminal – Frontend Application
 * Handles Real-Time Market Data, SSE Experiment Streaming, Chart Visualizations, and Results
 */

document.addEventListener("DOMContentLoaded", () => {
    // Application State
    const state = {
        models: ["XGBoost", "CatBoost", "LightGBM", "RandomForest", "Stacking Ensemble", "Stage Regression", "ARIMA", "SARIMAX", "LSTM"],
        selectedModels: ["XGBoost", "CatBoost", "LightGBM", "RandomForest", "Stacking Ensemble", "Stage Regression", "ARIMA", "SARIMAX", "LSTM"],
        metrics: ["MAE", "RMSE", "MAPE", "sMAPE", "R²", "Mean Error (Bias)", "Directional Accuracy", "UP Accuracy", "DOWN Accuracy", "Max Absolute Error", "Error Std Dev"],
        selectedMetrics: ["RMSE", "MAE"],
        selectedHorizons: [1, 7, 15, 30, 60, 90],
        horizonMode: "fixed",
        continuousRanges: {
            "1-7": Array.from({ length: 7 }, (_, i) => i + 1),
            "1-15": Array.from({ length: 15 }, (_, i) => i + 1),
            "1-30": Array.from({ length: 30 }, (_, i) => i + 1),
            "1-60": Array.from({ length: 60 }, (_, i) => i + 1),
            "1-90": Array.from({ length: 90 }, (_, i) => i + 1)
        },
        selectedRangeKey: "1-7",
        selectedRatios: ["60-40", "70-30", "75-25", "80-20", "85-15"],
        autoTuning: false,
        activeJobId: null,
        eventSource: null,
        results: [],
        chartInstance: null,
        cardComparisonCharts: {},
        uploadedActualData: [],
        uploadedActualFilename: "",
        chartMode: "forecast", // "forecast" or "historical"
        chartSelectedModel: "ALL",
        chartSelectedRatio: "ALL",
        chartSelectedMetric: "ALL",
        metricFilterCategory: "all",
        metricFilterSingle: "ALL",
        metricFilterGrade: "ALL",
        currentComparisonMetrics: null,
        chartHorizonSlice: "ALL",
        chartTimeframePeriod: 60,
        chartZoomIndex: 0,
        historicalData: [],
        activeExpandedCard: null,
        modalChartInstance: null,
        currentPage: 1,
        pageSize: "25",
        currentFilteredResults: []
    };

    // DOM Elements
    const elements = {
        topCopperPrice: document.getElementById("top-copper-price"),
        topCopperChange: document.getElementById("top-copper-change"),
        marketDateMeta: document.getElementById("market-date-meta"),
        cardCopperOpen: document.getElementById("card-copper-open"),
        cardCopperHigh: document.getElementById("card-copper-high"),
        cardCopperLow: document.getElementById("card-copper-low"),
        cardCopperClose: document.getElementById("card-copper-close"),
        cardCopperChange: document.getElementById("card-copper-change"),
        cardCopperStock: document.getElementById("card-copper-stock"),
        cardCrudeOil: document.getElementById("card-crude-oil"),
        cardDxyIndex: document.getElementById("card-dxy-index"),
        cardInterestRate: document.getElementById("card-interest-rate"),
        cardBasisSpread: document.getElementById("card-basis-spread"),
        
        // Multi-select dropdowns
        modelsDropdownBtn: document.getElementById("models-dropdown-btn"),
        modelsDropdownText: document.getElementById("models-dropdown-text"),
        modelsOptionsList: document.getElementById("models-options-list"),
        modelsSelectedCount: document.getElementById("models-selected-count"),
        chkSelectAllModels: document.getElementById("chk-select-all-models"),
        
        metricsDropdownBtn: document.getElementById("metrics-dropdown-btn"),
        metricsDropdownText: document.getElementById("metrics-dropdown-text"),
        metricsOptionsList: document.getElementById("metrics-options-list"),
        metricsSelectedCount: document.getElementById("metrics-selected-count"),
        chkSelectAllMetrics: document.getElementById("chk-select-all-metrics"),
        
        // Horizon Controls (Fixed vs Continuous)
        modeFixed: document.getElementById("mode-fixed"),
        modeContinuous: document.getElementById("mode-continuous"),
        fixedHorizonsPanel: document.getElementById("fixed-horizons-panel"),
        continuousHorizonsPanel: document.getElementById("continuous-horizons-panel"),
        horizonsChipsContainer: document.getElementById("horizons-chips-container"),
        continuousChipsContainer: document.getElementById("continuous-chips-container"),
        ratiosChipsContainer: document.getElementById("ratios-chips-container"),
        chkAutoTuning: document.getElementById("chk-auto-tuning"),
        
        btnRunForecast: document.getElementById("btn-run-forecast"),
        btnStopForecast: document.getElementById("btn-stop-forecast"),
        btnRefreshData: document.getElementById("btn-refresh-data"),
        fileCsvUpload: document.getElementById("file-csv-upload"),
        globalActualUpload: document.getElementById("global-actual-upload"),
        globalUploadBtnText: document.getElementById("global-upload-btn-text"),
        globalUploadStatusBadge: document.getElementById("global-upload-status-badge"),
        chartActualUpload: document.getElementById("chart-actual-upload"),
        
        // Progress Box
        progressContainer: document.getElementById("progress-container"),
        progressBarInner: document.getElementById("progress-bar-inner"),
        progressExpCounter: document.getElementById("progress-exp-counter"),
        progCurrentModel: document.getElementById("prog-current-model"),
        progCurrentHorizon: document.getElementById("prog-current-horizon"),
        progCurrentRatio: document.getElementById("prog-current-ratio"),
        progCurrentMetric: document.getElementById("prog-current-metric"),
        progPctText: document.getElementById("prog-pct-text"),
        
        // Visualizer Section & Controls
        mainVisualizerCard: document.getElementById("main-visualizer-card"),
        tabModeForecast: document.getElementById("tab-mode-forecast"),
        tabModeHistorical: document.getElementById("tab-mode-historical"),
        visualizerTitle: document.getElementById("visualizer-title"),
        visualizerSubTitle: document.getElementById("visualizer-sub-title"),
        chartModelSelect: document.getElementById("chart-model-select"),
        chartRatioSelect: document.getElementById("chart-ratio-select"),
        chartOptMetricSelect: document.getElementById("chart-opt-metric-select"),
        bannerModelGroup: document.getElementById("banner-model-group"),
        bannerRatioGroup: document.getElementById("banner-ratio-group"),
        bannerMetricGroup: document.getElementById("banner-metric-group"),
        bannerHorizonChip: document.getElementById("banner-horizon-chip"),
        bannerMatchedChip: document.getElementById("banner-matched-chip"),
        bannerPerfGrade: document.getElementById("banner-perf-grade"),
        bannerFileName: document.getElementById("banner-file-name"),
        chartUploadBtnText: document.getElementById("chart-upload-btn-text"),
        forecastRangeControls: document.getElementById("forecast-range-controls"),
        historicalTimeframeControls: document.getElementById("historical-timeframe-controls"),
        btnZoomIn: document.getElementById("btn-zoom-in"),
        btnZoomOut: document.getElementById("btn-zoom-out"),
        btnZoomReset: document.getElementById("btn-zoom-reset"),
        btnChartExpand: document.getElementById("btn-chart-expand"),
        btnExpandText: document.getElementById("btn-expand-text"),
        forecastCompMetricsPanel: document.getElementById("forecast-comparison-metrics-panel"),
        metricViewTabs: document.getElementById("metric-view-tabs"),
        metricSingleSelect: document.getElementById("metric-single-select"),
        metricGradeSelect: document.getElementById("metric-grade-select"),
        compMetricCardsGrid: document.getElementById("comp-metric-cards-grid"),
        chartTableDrawer: document.getElementById("chart-table-drawer"),
        btnToggleCompTable: document.getElementById("btn-toggle-comp-table"),
        drawerToggleText: document.getElementById("drawer-toggle-text"),
        drawerRowCount: document.getElementById("drawer-row-count"),
        compTableDrawerContent: document.getElementById("comp-table-drawer-content"),
        compDrawerTableBody: document.getElementById("comp-drawer-table-body"),
        mainForecastChart: document.getElementById("main-forecast-chart"),

        // Result Card Expand Modal Elements
        cardExpandModal: document.getElementById("card-expand-modal"),
        btnCloseExpandModal: document.getElementById("btn-close-expand-modal"),
        modalModelName: document.getElementById("modal-model-name"),
        modalHorizonLabel: document.getElementById("modal-horizon-label"),
        modalRatioLabel: document.getElementById("modal-ratio-label"),
        modalLeakageBadge: document.getElementById("modal-leakage-badge"),
        modalTargetMeta: document.getElementById("modal-target-meta"),
        modalPredPrice: document.getElementById("modal-pred-price"),
        modalActualPrice: document.getElementById("modal-actual-price"),
        modalDiffPrice: document.getElementById("modal-diff-price"),
        modalDirMatch: document.getElementById("modal-dir-match"),
        modalMatchedCount: document.getElementById("modal-matched-count"),
        modalExpandedChart: document.getElementById("modal-expanded-chart"),
        modalCompMetricsGrid: document.getElementById("modal-comp-metrics-grid"),
        modalCompTableBody: document.getElementById("modal-comp-table-body"),
        modalBtnZoomIn: document.getElementById("modal-btn-zoom-in"),
        modalBtnZoomOut: document.getElementById("modal-btn-zoom-out"),
        modalBtnZoomReset: document.getElementById("modal-btn-zoom-reset"),

        // Results Grid & Filters
        resultsCountBadge: document.getElementById("results-count-badge"),
        resultsEmptyPlaceholder: document.getElementById("results-empty-placeholder"),
        resultsGridContainer: document.getElementById("results-grid-container"),
        resultsGridBody: document.getElementById("results-grid-body"),
        resultsDataGrid: document.getElementById("results-data-grid"),
        gridPaginationBar: document.getElementById("grid-pagination-bar"),
        gridPageSizeSelect: document.getElementById("grid-page-size-select"),
        btnPagFirst: document.getElementById("btn-pag-first"),
        btnPagPrev: document.getElementById("btn-pag-prev"),
        btnPagNext: document.getElementById("btn-pag-next"),
        btnPagLast: document.getElementById("btn-pag-last"),
        pagStart: document.getElementById("pag-start"),
        pagEnd: document.getElementById("pag-end"),
        pagTotal: document.getElementById("pag-total"),
        pagCurrentPage: document.getElementById("pag-current-page"),
        pagTotalPages: document.getElementById("pag-total-pages"),
        resultMatrixContainer: document.getElementById("result-matrix-container"),
        matrixTableBody: document.getElementById("matrix-table-body"),
        filterHorizonSelect: document.getElementById("filter-horizon-select"),
        filterModelSelect: document.getElementById("filter-model-select"),
        btnViewCards: document.getElementById("btn-view-cards"),
        btnViewMatrix: document.getElementById("btn-view-matrix"),
        btnExportCsv: document.getElementById("btn-export-csv"),
        btnExportJson: document.getElementById("btn-export-json")
    };

    // =========================================================================
    // 1. Initialization & Data Fetching
    // =========================================================================

    async function initApp() {
        setupEventListeners();
        setupDropdowns();
        setupChips();
        await fetchMarketSummary();
        await fetchHistoricalData(180);
    }

    async function fetchMarketSummary() {
        try {
            const res = await fetch("/api/market-summary");
            const json = await res.json();
            if (json.status === "success" && json.data) {
                renderMarketSummary(json.data);
            }
        } catch (err) {
            console.error("Failed to fetch market summary:", err);
        }
    }

    function renderMarketSummary(d) {
        const fmtPrice = (v) => `$${Number(v).toFixed(4)}`;
        const fmtChange = (chg, pct) => {
            const sign = chg >= 0 ? "+" : "";
            return `${sign}$${Number(chg).toFixed(4)} (${sign}${Number(pct).toFixed(2)}%)`;
        };

        if (elements.topCopperPrice) elements.topCopperPrice.textContent = fmtPrice(d.copper_close);
        if (elements.topCopperChange) {
            const isPos = d.copper_change >= 0;
            elements.topCopperChange.textContent = `${isPos ? "+" : ""}${Number(d.copper_pct_change).toFixed(2)}%`;
            elements.topCopperChange.className = `ticker-badge ${isPos ? "positive" : "negative"}`;
        }
        
        if (elements.marketDateMeta) elements.marketDateMeta.textContent = `Latest Session: ${d.date || "N/A"}`;
        if (elements.cardCopperOpen) elements.cardCopperOpen.textContent = fmtPrice(d.copper_open);
        if (elements.cardCopperHigh) elements.cardCopperHigh.textContent = fmtPrice(d.copper_high);
        if (elements.cardCopperLow) elements.cardCopperLow.textContent = fmtPrice(d.copper_low);
        if (elements.cardCopperClose) elements.cardCopperClose.textContent = fmtPrice(d.copper_close);
        
        if (elements.cardCopperChange) {
            const isPos = d.copper_change >= 0;
            elements.cardCopperChange.textContent = fmtChange(d.copper_change, d.copper_pct_change);
            elements.cardCopperChange.className = `card-change ${isPos ? "positive" : "negative"}`;
        }
        
        if (elements.cardCopperStock) elements.cardCopperStock.textContent = `${Number(d.copper_stock).toLocaleString()} MT`;
        if (elements.cardCrudeOil) elements.cardCrudeOil.textContent = `$${Number(d.crude_oil).toFixed(2)} /bbl`;
        if (elements.cardDxyIndex) elements.cardDxyIndex.textContent = `${Number(d.dxy_index).toFixed(2)}`;
        if (elements.cardInterestRate) elements.cardInterestRate.textContent = `${Number(d.interest_rate).toFixed(2)}%`;
        if (elements.cardBasisSpread) {
            const spreadSign = d.basis_spread >= 0 ? "+" : "";
            const spreadType = d.basis_spread >= 0 ? "Contango" : "Backwardation";
            elements.cardBasisSpread.textContent = `3M Basis: ${spreadSign}$${Number(d.basis_spread).toFixed(2)}/t (${spreadType})`;
        }
    }

    async function fetchHistoricalData(limit = 180) {
        try {
            state.chartTimeframePeriod = limit;
            const res = await fetch(`/api/historical-data?limit=${limit}`);
            const json = await res.json();
            if (json.status === "success" && json.data) {
                state.historicalData = json.data;
                updateMainVisualizer();
            }
        } catch (err) {
            console.error("Failed to load historical data for chart:", err);
        }
    }

    // =========================================================================
    // 2. Multi-Mode Visualization & Interactive Comparison Engine
    // =========================================================================

    // Metric definitions and interpretative metadata
    const METRIC_DEFINITIONS = {
        "Directional Accuracy": { category: "directional", format: v => `${v.toFixed(1)}%`, desc: "Percentage of trading days where predicted price movement direction correctly matched actual market trend." },
        "UP Accuracy": { category: "directional", format: v => `${v.toFixed(1)}%`, desc: "Accuracy of predicted upward (bullish) movements against real upward days." },
        "DOWN Accuracy": { category: "directional", format: v => `${v.toFixed(1)}%`, desc: "Accuracy of predicted downward (bearish) movements against real downward days." },
        "MAE": { category: "primary", format: v => `$${v.toFixed(4)}`, desc: "Mean Absolute Error: average magnitude of absolute prediction errors in dollar terms." },
        "RMSE": { category: "primary", format: v => `$${v.toFixed(4)}`, desc: "Root Mean Squared Error: standard deviation of prediction residuals (penalizes large swings)." },
        "MAPE": { category: "primary", format: v => `${v.toFixed(2)}%`, desc: "Mean Absolute Percentage Error: relative forecast accuracy across horizons." },
        "sMAPE": { category: "error", format: v => `${v.toFixed(2)}%`, desc: "Symmetric MAPE: robust bounded percentage error preventing distortion from extreme points." },
        "R²": { category: "primary", format: v => v.toFixed(4), desc: "Coefficient of Determination: proportion of market variance explained by model trajectory." },
        "Mean Error (Bias)": { category: "error", format: v => `${v >= 0 ? '+' : ''}$${v.toFixed(4)}`, desc: "Systematic directional forecast bias indicating whether the model overshoots or undershoots." },
        "Max Absolute Error": { category: "error", format: v => `$${v.toFixed(4)}`, desc: "Maximum worst-case dollar deviation across all tested target dates." },
        "Error Std Dev": { category: "error", format: v => `$${v.toFixed(4)}`, desc: "Standard deviation of prediction errors reflecting forecast stability." }
    };

    function getMetricPerformanceTier(key, val) {
        if (typeof val !== "number" || isNaN(val)) {
            return { tier: "tier-average", label: "⚠️ Average", grade: "AVERAGE", colorClass: "cyan" };
        }

        switch (key) {
            case "Directional Accuracy":
            case "UP Accuracy":
            case "DOWN Accuracy":
                if (val >= 70) return { tier: "tier-best", label: "⭐ Best", grade: "BEST", colorClass: "green" };
                if (val >= 58) return { tier: "tier-good", label: "✅ Good", grade: "GOOD", colorClass: "green" };
                if (val >= 48) return { tier: "tier-average", label: "⚠️ Average", grade: "AVERAGE", colorClass: "amber" };
                return { tier: "tier-poor", label: "❌ Poor", grade: "POOR", colorClass: "purple" };

            case "MAPE":
            case "sMAPE":
                if (val <= 2.0) return { tier: "tier-best", label: "⭐ Best", grade: "BEST", colorClass: "green" };
                if (val <= 4.0) return { tier: "tier-good", label: "✅ Good", grade: "GOOD", colorClass: "cyan" };
                if (val <= 7.0) return { tier: "tier-average", label: "⚠️ Average", grade: "AVERAGE", colorClass: "amber" };
                return { tier: "tier-poor", label: "❌ Poor", grade: "POOR", colorClass: "purple" };

            case "MAE":
            case "RMSE":
            case "Max Absolute Error":
            case "Error Std Dev":
                if (val <= 0.10) return { tier: "tier-best", label: "⭐ Best", grade: "BEST", colorClass: "green" };
                if (val <= 0.20) return { tier: "tier-good", label: "✅ Good", grade: "GOOD", colorClass: "cyan" };
                if (val <= 0.35) return { tier: "tier-average", label: "⚠️ Average", grade: "AVERAGE", colorClass: "amber" };
                return { tier: "tier-poor", label: "❌ Poor", grade: "POOR", colorClass: "purple" };

            case "Mean Error (Bias)":
                if (Math.abs(val) <= 0.05) return { tier: "tier-best", label: "⭐ Best", grade: "BEST", colorClass: "green" };
                if (Math.abs(val) <= 0.15) return { tier: "tier-good", label: "✅ Good", grade: "GOOD", colorClass: "cyan" };
                return { tier: "tier-average", label: "⚠️ Average", grade: "AVERAGE", colorClass: "amber" };

            case "R²":
                if (val >= 0.70) return { tier: "tier-best", label: "⭐ Best", grade: "BEST", colorClass: "green" };
                if (val >= 0.35) return { tier: "tier-good", label: "✅ Good", grade: "GOOD", colorClass: "cyan" };
                if (val >= 0.00) return { tier: "tier-average", label: "⚠️ Average", grade: "AVERAGE", colorClass: "amber" };
                return { tier: "tier-poor", label: "❌ Poor", grade: "POOR", colorClass: "purple" };

            default:
                return { tier: "tier-good", label: "✅ Good", grade: "GOOD", colorClass: "cyan" };
        }
    }

    function populateChartControlsDropdowns() {
        if (!state.results || state.results.length === 0) return;

        // 1. Model Dropdown
        const distinctModels = Array.from(new Set(state.results.map(r => r.model))).sort();
        if (elements.chartModelSelect) {
            const currentModel = state.chartSelectedModel;
            elements.chartModelSelect.innerHTML = `<option value="ALL">Best Across Horizons</option>` + 
                distinctModels.map(m => `<option value="${m}" ${m === currentModel ? 'selected' : ''}>${m}</option>`).join("");
        }

        // 2. Ratio Dropdown
        const modelRecords = state.chartSelectedModel === "ALL" 
            ? state.results 
            : state.results.filter(r => r.model === state.chartSelectedModel);
        
        const distinctRatios = Array.from(new Set(modelRecords.map(r => r.ratio))).sort();
        if (elements.chartRatioSelect) {
            const currentRatio = state.chartSelectedRatio;
            elements.chartRatioSelect.innerHTML = `<option value="ALL">All Ratios (Best)</option>` + 
                distinctRatios.map(rt => `<option value="${rt}" ${rt === currentRatio ? 'selected' : ''}>${rt}</option>`).join("");
        }

        // 3. Optimization Metric Dropdown
        const distinctMetrics = Array.from(new Set(modelRecords.map(r => r.metric_name))).sort();
        if (elements.chartOptMetricSelect) {
            const currentMetric = state.chartSelectedMetric;
            elements.chartOptMetricSelect.innerHTML = `<option value="ALL">Best Overall</option>` + 
                distinctMetrics.map(mt => `<option value="${mt}" ${mt === currentMetric ? 'selected' : ''}>${mt}</option>`).join("");
        }
    }

    function renderComparisonMetricsPanel(metrics) {
        if (!elements.forecastCompMetricsPanel || !elements.compMetricCardsGrid || !metrics) return;
        state.currentComparisonMetrics = metrics;
        elements.forecastCompMetricsPanel.style.display = "flex";

        // Overall Performance Grade for banner badge
        const dirAcc = metrics["Directional Accuracy"] || 0;
        const mape = metrics["MAPE"] || 0;
        let overallTier = { tier: "tier-good", label: "✅ Good Performance" };
        if (dirAcc >= 70 && mape <= 3.5) {
            overallTier = { tier: "tier-best", label: "⭐ Best Performance" };
        } else if (dirAcc >= 58 && mape <= 5.5) {
            overallTier = { tier: "tier-good", label: "✅ Good Performance" };
        } else if (dirAcc >= 48) {
            overallTier = { tier: "tier-average", label: "⚠️ Average Performance" };
        } else {
            overallTier = { tier: "tier-poor", label: "❌ High Error Variance" };
        }

        if (elements.bannerPerfGrade) {
            elements.bannerPerfGrade.style.display = "inline-flex";
            elements.bannerPerfGrade.className = `banner-stat-chip grade-badge ${overallTier.tier}`;
            elements.bannerPerfGrade.textContent = overallTier.label;
        }

        // Filter and Build Cards
        const cardItems = [];
        const primaryList = ["MAE", "RMSE", "MAPE", "R²", "Directional Accuracy"];
        const accuracyList = ["Directional Accuracy", "UP Accuracy", "DOWN Accuracy", "R²"];
        const errorList = ["MAE", "RMSE", "MAPE", "sMAPE", "Max Absolute Error", "Mean Error (Bias)", "Error Std Dev"];
        const directionalList = ["Directional Accuracy", "UP Accuracy", "DOWN Accuracy"];

        Object.entries(metrics).forEach(([mKey, mVal]) => {
            const def = METRIC_DEFINITIONS[mKey] || { category: "other", format: v => v, desc: "" };
            const tierInfo = getMetricPerformanceTier(mKey, mVal);
            
            // Category filter check
            let matchesCategory = true;
            if (state.metricFilterCategory === "best") {
                matchesCategory = (tierInfo.grade === "BEST" || tierInfo.grade === "GOOD");
            } else if (state.metricFilterCategory === "primary") {
                matchesCategory = primaryList.includes(mKey);
            } else if (state.metricFilterCategory === "accuracy") {
                matchesCategory = accuracyList.includes(mKey);
            } else if (state.metricFilterCategory === "error") {
                matchesCategory = errorList.includes(mKey);
            } else if (state.metricFilterCategory === "directional") {
                matchesCategory = directionalList.includes(mKey);
            }

            // Single metric filter check
            let matchesSingle = (state.metricFilterSingle === "ALL" || state.metricFilterSingle === mKey);

            // Grade filter check
            let matchesGrade = (state.metricFilterGrade === "ALL" || state.metricFilterGrade === tierInfo.grade);

            if (matchesCategory && matchesSingle && matchesGrade) {
                cardItems.push({
                    key: mKey,
                    val: mVal,
                    formattedVal: def.format(mVal),
                    category: def.category,
                    desc: def.desc,
                    tierInfo: tierInfo
                });
            }
        });

        if (cardItems.length === 0) {
            elements.compMetricCardsGrid.innerHTML = `
                <div style="grid-column: 1/-1; padding: 18px; text-align: center; color: var(--text-muted); font-size: 11px; background: rgba(0,0,0,0.25); border-radius: 8px;">
                    No metrics match the selected filter criteria. Choose <strong>"All Metrics"</strong> or <strong>"All Grades"</strong> above to view all results.
                </div>
            `;
            return;
        }

        elements.compMetricCardsGrid.innerHTML = cardItems.map(item => `
            <div class="metric-comp-card" data-metric="${item.key}">
                <div class="metric-card-top">
                    <span class="metric-category-tag">${item.category}</span>
                    <span class="perf-tier-badge ${item.tierInfo.tier}">${item.tierInfo.label}</span>
                </div>
                <div class="metric-card-title">${item.key}</div>
                <div class="metric-card-value ${item.tierInfo.colorClass}">${item.formattedVal}</div>
                <div class="metric-card-footer">${item.desc}</div>
            </div>
        `).join("");
    }

    function updateMainVisualizer() {
        if (!elements.mainForecastChart) return;

        if (state.chartMode === "forecast") {
            if (elements.tabModeForecast) elements.tabModeForecast.classList.add("active");
            if (elements.tabModeHistorical) elements.tabModeHistorical.classList.remove("active");
            if (elements.forecastRangeControls) elements.forecastRangeControls.style.display = "flex";
            if (elements.historicalTimeframeControls) elements.historicalTimeframeControls.style.display = "none";
            if (elements.bannerModelGroup) elements.bannerModelGroup.style.display = "flex";
            if (elements.bannerRatioGroup) elements.bannerRatioGroup.style.display = "flex";
            if (elements.bannerMetricGroup) elements.bannerMetricGroup.style.display = "flex";
            if (elements.visualizerTitle) elements.visualizerTitle.textContent = "COPPER FORECAST VS ACTUAL COMPARISON";
            if (elements.visualizerSubTitle) elements.visualizerSubTitle.textContent = "Direct Day-by-Day Forecast Targets vs Uploaded Ground Truth";

            renderForecastVsActualChart();
        } else {
            if (elements.tabModeHistorical) elements.tabModeHistorical.classList.add("active");
            if (elements.tabModeForecast) elements.tabModeForecast.classList.remove("active");
            if (elements.forecastRangeControls) elements.forecastRangeControls.style.display = "none";
            if (elements.historicalTimeframeControls) elements.historicalTimeframeControls.style.display = "flex";
            if (elements.bannerModelGroup) elements.bannerModelGroup.style.display = "none";
            if (elements.bannerRatioGroup) elements.bannerRatioGroup.style.display = "none";
            if (elements.bannerMetricGroup) elements.bannerMetricGroup.style.display = "none";
            if (elements.forecastCompMetricsPanel) elements.forecastCompMetricsPanel.style.display = "none";
            if (elements.bannerPerfGrade) elements.bannerPerfGrade.style.display = "none";
            if (elements.chartTableDrawer) elements.chartTableDrawer.style.display = "none";
            if (elements.visualizerTitle) elements.visualizerTitle.textContent = "COPPER PRICE HISTORICAL OVERVIEW & PROJECTION";
            if (elements.visualizerSubTitle) elements.visualizerSubTitle.textContent = "Historical Daily Close & Forward Direct Forecasting Projection";

            renderHistoricalChart();
        }
    }

    function renderForecastVsActualChart() {
        const ctx = elements.mainForecastChart.getContext("2d");

        // If no results are available yet, show historical view
        if (!state.results || state.results.length === 0) {
            renderHistoricalChart();
            if (elements.bannerHorizonChip) elements.bannerHorizonChip.textContent = "Run Forecast to View Predictions";
            if (elements.forecastCompMetricsPanel) elements.forecastCompMetricsPanel.style.display = "none";
            if (elements.bannerPerfGrade) elements.bannerPerfGrade.style.display = "none";
            return;
        }

        // Populate Model, Ratio, and Metric Dropdowns in Chart Banner
        populateChartControlsDropdowns();

        // 1. Filter results according to active Model, Ratio, and Metric choices
        let filtered = state.results || [];
        if (state.chartSelectedModel !== "ALL") {
            filtered = filtered.filter(r => r.model === state.chartSelectedModel);
        }
        if (state.chartSelectedRatio && state.chartSelectedRatio !== "ALL") {
            filtered = filtered.filter(r => r.ratio === state.chartSelectedRatio);
        }
        if (state.chartSelectedMetric && state.chartSelectedMetric !== "ALL") {
            filtered = filtered.filter(r => r.metric_name === state.chartSelectedMetric);
        }

        // Deduplicate: Pick exactly 1 best point per horizon day (eliminating duplicate repeated dates on the chart)
        const bestPerHorizon = {};
        filtered.forEach(r => {
            if (!bestPerHorizon[r.horizon] || r.metric_score < bestPerHorizon[r.horizon].metric_score) {
                bestPerHorizon[r.horizon] = r;
            }
        });

        let sequence = Object.values(bestPerHorizon).sort((a, b) => a.horizon - b.horizon);
        if (sequence.length === 0 && state.results.length > 0) {
            sequence = state.results.slice(0, 15);
        }

        // 2. Apply Horizon Slice (e.g. 7D, 15D, 30D, 60D, 90D)
        let visibleSequence = [...sequence];
        if (state.chartHorizonSlice !== "ALL") {
            const sliceLimit = parseInt(state.chartHorizonSlice);
            if (!isNaN(sliceLimit)) {
                visibleSequence = sequence.filter(s => s.horizon <= sliceLimit);
                if (visibleSequence.length === 0) visibleSequence = sequence.slice(0, sliceLimit);
            }
        }

        // 3. Build Date Maps & Aligned Arrays
        const actualMap = new Map((state.uploadedActualData || []).map(r => [r.date, r.actual_close]));
        const labels = visibleSequence.map(s => s.target_date);
        const predPrices = visibleSequence.map(s => Number(s.predicted_price));
        const actualPrices = visibleSequence.map(s => actualMap.has(s.target_date) ? Number(actualMap.get(s.target_date)) : null);

        // Matched pairs for comparison calculation
        const matchedPairs = [];
        visibleSequence.forEach(s => {
            if (actualMap.has(s.target_date)) {
                matchedPairs.push({ pred: Number(s.predicted_price), actual: Number(actualMap.get(s.target_date)) });
            }
        });

        // 4. Update Banner Details
        if (elements.bannerHorizonChip) {
            elements.bannerHorizonChip.textContent = `Horizon: 1 to ${visibleSequence.length} Days (${visibleSequence[0]?.target_date || ""} → ${visibleSequence[visibleSequence.length - 1]?.target_date || ""})`;
        }

        if (state.uploadedActualData && state.uploadedActualData.length > 0) {
            if (elements.bannerMatchedChip) {
                elements.bannerMatchedChip.style.display = "inline-flex";
                elements.bannerMatchedChip.textContent = `🎯 Matched: ${matchedPairs.length} / ${visibleSequence.length} Days`;
                if (matchedPairs.length < visibleSequence.length) {
                    elements.bannerMatchedChip.className = "banner-stat-chip";
                    elements.bannerMatchedChip.style.borderColor = "var(--accent-gold)";
                    elements.bannerMatchedChip.style.color = "var(--accent-gold)";
                } else {
                    elements.bannerMatchedChip.className = "banner-stat-chip green";
                    elements.bannerMatchedChip.style.borderColor = "";
                    elements.bannerMatchedChip.style.color = "";
                }
            }
            if (elements.bannerFileName) {
                elements.bannerFileName.textContent = `📄 ${state.uploadedActualFilename || "Actual Data"}`;
            }
            if (elements.chartUploadBtnText) {
                elements.chartUploadBtnText.textContent = "📁 Replace Actual Data";
            }
        } else {
            if (elements.bannerMatchedChip) elements.bannerMatchedChip.style.display = "none";
            if (elements.bannerFileName) elements.bannerFileName.textContent = "";
            if (elements.chartUploadBtnText) elements.chartUploadBtnText.textContent = "📁 Upload Actual Data";
            if (elements.bannerPerfGrade) elements.bannerPerfGrade.style.display = "none";
        }

        // 5. Update Comprehensive Comparison Metrics Panel
        if (matchedPairs.length > 0) {
            const metrics = calculateComparisonMetrics(matchedPairs, visibleSequence[0]?.latest_price);
            if (metrics) {
                renderComparisonMetricsPanel(metrics);
            }
        } else {
            if (elements.forecastCompMetricsPanel) elements.forecastCompMetricsPanel.style.display = "none";
            if (elements.bannerPerfGrade) elements.bannerPerfGrade.style.display = "none";
        }

        // 6. Populate Expandable Table Drawer
        if (elements.chartTableDrawer) {
            elements.chartTableDrawer.style.display = "block";
            if (elements.drawerRowCount) elements.drawerRowCount.textContent = `${visibleSequence.length} Forecast Days`;
            if (elements.compDrawerTableBody) {
                elements.compDrawerTableBody.innerHTML = visibleSequence.map((s, idx) => {
                    const act = actualMap.has(s.target_date) ? actualMap.get(s.target_date) : null;
                    const pred = Number(s.predicted_price);
                    let diffText = "— Pending";
                    let diffClass = "neutral";
                    let errPctText = "—";
                    let dirText = "—";

                    if (act !== null) {
                        const diff = pred - act;
                        const sign = diff >= 0 ? "+" : "";
                        diffText = `${sign}$${diff.toFixed(4)}`;
                        diffClass = Math.abs(diff) < 0.05 ? "positive" : (diff > 0 ? "positive" : "negative");
                        const errPct = (Math.abs(diff) / act) * 100;
                        errPctText = `${errPct.toFixed(2)}%`;

                        const origin = s.latest_price || pred;
                        const matchDir = Math.sign(pred - origin) === Math.sign(act - origin);
                        dirText = matchDir ? `<span style="color: var(--accent-green);">✓ MATCHED</span>` : `<span style="color: var(--accent-red);">✗ DIVERGED</span>`;
                    }

                    return `
                        <tr>
                            <td><strong>Day ${idx + 1}</strong> (${s.horizon_label || `${s.horizon}D`})</td>
                            <td>${s.target_date}</td>
                            <td style="color: #06b6d4; font-weight: 700;">$${pred.toFixed(4)}</td>
                            <td style="color: ${act !== null ? "#f59e0b" : "var(--text-subtle)"}; font-weight: 700;">${act !== null ? `$${act.toFixed(4)}` : "— Pending"}</td>
                            <td><span class="diff-badge ${diffClass}">${diffText}</span></td>
                            <td>${errPctText}</td>
                            <td>${dirText}</td>
                        </tr>
                    `;
                }).join("");
            }
        }

        // 7. Auto Tight Y-Axis Scale with padding
        const allPrices = [...predPrices, ...actualPrices.filter(v => v !== null)];
        const minP = Math.min(...allPrices);
        const maxP = Math.max(...allPrices);
        const spread = (maxP - minP) || 0.1;
        const padding = spread * 0.18;
        const yMin = Number((minP - padding).toFixed(2));
        const yMax = Number((maxP + padding).toFixed(2));

        // 8. Render Chart.js
        if (state.chartInstance) {
            state.chartInstance.destroy();
        }

        state.chartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Predicted Copper Price ($/lb)",
                        data: predPrices,
                        borderColor: "#06b6d4",
                        backgroundColor: "rgba(6, 182, 212, 0.12)",
                        borderWidth: 3.5,
                        pointStyle: "circle",
                        pointRadius: 6,
                        pointHoverRadius: 9,
                        pointBackgroundColor: "#06b6d4",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: `Uploaded Actual Close ($/lb) ${state.uploadedActualFilename ? `(${state.uploadedActualFilename})` : ""}`,
                        data: actualPrices,
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.15)",
                        borderWidth: 3,
                        borderDash: [6, 4],
                        pointStyle: "rectRot",
                        pointRadius: 8,
                        pointHoverRadius: 11,
                        pointBackgroundColor: "#f59e0b",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        fill: false,
                        spanGaps: true,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            color: "#e5e7eb",
                            font: { family: "Inter", size: 12, weight: 700 },
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: "#111827",
                        titleColor: "#38bdf8",
                        titleFont: { family: "Inter", size: 13, weight: 700 },
                        bodyColor: "#f3f4f6",
                        bodyFont: { family: "JetBrains Mono", size: 12 },
                        borderColor: "#06b6d4",
                        borderWidth: 1.5,
                        padding: 12,
                        callbacks: {
                            title: function(items) {
                                const idx = items[0].dataIndex;
                                return `📅 Date: ${labels[idx]} (Day ${idx + 1} of ${labels.length})`;
                            },
                            label: function(ctx) {
                                const idx = ctx.dataIndex;
                                const pred = predPrices[idx];
                                const act = actualPrices[idx];
                                if (ctx.datasetIndex === 0) {
                                    return `  Predicted Price: $${pred.toFixed(4)}`;
                                } else {
                                    if (act === null) {
                                        return `  Actual Price: Not Uploaded`;
                                    }
                                    const diff = pred - act;
                                    const pct = (Math.abs(diff) / act) * 100;
                                    const sign = diff >= 0 ? "+" : "";
                                    return [
                                        `  Actual Price:    $${act.toFixed(4)}`,
                                        `  Difference:      ${sign}$${diff.toFixed(4)} (${pct.toFixed(2)}%)`
                                    ];
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { family: "JetBrains Mono", size: 11, weight: 600 },
                            maxRotation: 45
                        }
                    },
                    y: {
                        min: yMin,
                        max: yMax,
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { family: "JetBrains Mono", size: 11 },
                            callback: v => `$${Number(v).toFixed(2)}`
                        }
                    }
                }
            }
        });
    }

    function renderHistoricalChart() {
        const ctx = elements.mainForecastChart.getContext("2d");
        const histData = state.historicalData || [];
        const labels = histData.map(d => d.date);
        const prices = histData.map(d => d.close);

        const forecastPoints = [];
        if (state.results && state.results.length > 0) {
            const bestPerHorizon = {};
            state.results.forEach(r => {
                if (!bestPerHorizon[r.horizon] || r.metric_score < bestPerHorizon[r.horizon].metric_score) {
                    bestPerHorizon[r.horizon] = r;
                }
            });
            forecastPoints.push(...Object.values(bestPerHorizon));
        }

        const forecastMap = {};
        forecastPoints.forEach(p => {
            forecastMap[p.target_date] = p.predicted_price;
        });

        const allLabels = [...labels];
        forecastPoints.forEach(p => {
            if (!allLabels.includes(p.target_date)) {
                allLabels.push(p.target_date);
            }
        });
        allLabels.sort();

        const histSeries = allLabels.map(lbl => {
            const found = histData.find(d => d.date === lbl);
            return found ? found.close : null;
        });

        const forecastSeries = allLabels.map(lbl => {
            if (forecastMap[lbl] !== undefined) return forecastMap[lbl];
            if (lbl === labels[labels.length - 1]) return prices[prices.length - 1];
            return null;
        });

        if (state.chartInstance) {
            state.chartInstance.destroy();
        }

        state.chartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: allLabels,
                datasets: [
                    {
                        label: "Historical Copper Close ($/lb)",
                        data: histSeries,
                        borderColor: "#3b82f6",
                        backgroundColor: "rgba(59, 130, 246, 0.08)",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.15,
                        pointRadius: 0,
                        pointHoverRadius: 5
                    },
                    {
                        label: "Multi-Horizon Direct Forecasts",
                        data: forecastSeries,
                        borderColor: "#10b981",
                        backgroundColor: "rgba(16, 185, 129, 0.15)",
                        borderWidth: 2.5,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 6,
                        pointBackgroundColor: "#10b981",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 1.5,
                        pointHoverRadius: 8
                    },
                    ...(state.uploadedActualData && state.uploadedActualData.length > 0 ? [{
                        label: `Uploaded Actual Market Close (${state.uploadedActualFilename || "Actual Data"})`,
                        data: allLabels.map(lbl => {
                            const found = state.uploadedActualData.find(r => r.date === lbl);
                            return found ? found.actual_close : null;
                        }),
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.2)",
                        borderWidth: 2.5,
                        pointRadius: 6,
                        pointBackgroundColor: "#f59e0b",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 1.5,
                        pointHoverRadius: 8,
                        spanGaps: true
                    }] : [])
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            color: "#9ca3af",
                            font: { family: "Inter", size: 11, weight: 600 },
                            usePointStyle: true
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.04)" },
                        ticks: { color: "#6b7280", font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 12 }
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.06)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { family: "JetBrains Mono", size: 10 },
                            callback: v => `$${Number(v).toFixed(2)}`
                        }
                    }
                }
            }
        });
    }

    function populateChartModelDropdown() {
        if (!elements.chartModelSelect) return;
        const currentVal = state.chartSelectedModel || "ALL";
        const models = Array.from(new Set((state.results || []).map(r => r.model)));

        elements.chartModelSelect.innerHTML = '<option value="ALL">ALL (Best per Horizon)</option>';
        models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            elements.chartModelSelect.appendChild(opt);
        });
        elements.chartModelSelect.value = models.includes(currentVal) ? currentVal : "ALL";
    }

    // =========================================================================
    // 3. Dropdowns & Controls Interactivity
    // =========================================================================

    function setupDropdowns() {
        // Toggle Dropdowns
        if (elements.modelsDropdownBtn) {
            elements.modelsDropdownBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                elements.modelsOptionsList.classList.toggle("open");
                elements.metricsOptionsList.classList.remove("open");
            });
        }

        if (elements.metricsDropdownBtn) {
            elements.metricsDropdownBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                elements.metricsOptionsList.classList.toggle("open");
                elements.modelsOptionsList.classList.remove("open");
            });
        }

        // Prevent dropdown from closing when clicking inside the options list
        if (elements.modelsOptionsList) {
            elements.modelsOptionsList.addEventListener("click", (e) => {
                e.stopPropagation();
            });
        }

        if (elements.metricsOptionsList) {
            elements.metricsOptionsList.addEventListener("click", (e) => {
                e.stopPropagation();
            });
        }

        document.addEventListener("click", (e) => {
            if (elements.modelsOptionsList && !elements.modelsDropdownBtn?.contains(e.target) && !elements.modelsOptionsList?.contains(e.target)) {
                elements.modelsOptionsList.classList.remove("open");
            }
            if (elements.metricsOptionsList && !elements.metricsDropdownBtn?.contains(e.target) && !elements.metricsOptionsList?.contains(e.target)) {
                elements.metricsOptionsList.classList.remove("open");
            }
        });

        // Model Checkboxes
        const modelCheckboxes = document.querySelectorAll("input[name='model-chk']");
        modelCheckboxes.forEach(chk => {
            chk.addEventListener("change", () => {
                updateSelectedModels();
            });
        });

        if (elements.chkSelectAllModels) {
            elements.chkSelectAllModels.addEventListener("change", (e) => {
                const isChecked = e.target.checked;
                modelCheckboxes.forEach(chk => chk.checked = isChecked);
                updateSelectedModels();
            });
        }

        // Metric Checkboxes
        const metricCheckboxes = document.querySelectorAll("input[name='metric-chk']");
        metricCheckboxes.forEach(chk => {
            chk.addEventListener("change", () => {
                updateSelectedMetrics();
            });
        });

        if (elements.chkSelectAllMetrics) {
            elements.chkSelectAllMetrics.addEventListener("change", (e) => {
                const isChecked = e.target.checked;
                metricCheckboxes.forEach(chk => chk.checked = isChecked);
                updateSelectedMetrics();
            });
        }

        // Auto Tuning Toggle
        if (elements.chkAutoTuning) {
            elements.chkAutoTuning.addEventListener("change", (e) => {
                state.autoTuning = e.target.checked;
            });
        }
    }

    function updateSelectedModels() {
        const checked = Array.from(document.querySelectorAll("input[name='model-chk']:checked")).map(c => c.value);
        state.selectedModels = checked;
        if (elements.modelsSelectedCount) elements.modelsSelectedCount.textContent = `${checked.length} Selected`;
        if (elements.modelsDropdownText) {
            elements.modelsDropdownText.textContent = checked.length === 9 
                ? "All 9 Models Selected" 
                : checked.length > 0 ? `${checked.length} Model(s) Selected` : "Select Models...";
        }
        if (elements.chkSelectAllModels) {
            elements.chkSelectAllModels.checked = checked.length === 9;
        }
        populateModelFilterOptions(checked);
    }

    function updateSelectedMetrics() {
        const checked = Array.from(document.querySelectorAll("input[name='metric-chk']:checked")).map(c => c.value);
        state.selectedMetrics = checked;
        if (elements.metricsSelectedCount) elements.metricsSelectedCount.textContent = `${checked.length} Selected`;
        if (elements.metricsDropdownText) {
            elements.metricsDropdownText.textContent = checked.length === 11
                ? "All 11 Metrics Selected"
                : checked.length > 0 ? checked.join(", ") : "Select Error Metrics...";
        }
        if (elements.chkSelectAllMetrics) {
            elements.chkSelectAllMetrics.checked = checked.length === 11;
        }
    }

    function setupChips() {
        // Horizon Mode Switch (Fixed vs Continuous Daily)
        if (elements.modeFixed && elements.modeContinuous) {
            elements.modeFixed.addEventListener("change", () => {
                if (elements.modeFixed.checked) {
                    state.horizonMode = "fixed";
                    if (elements.fixedHorizonsPanel) elements.fixedHorizonsPanel.style.display = "block";
                    if (elements.continuousHorizonsPanel) elements.continuousHorizonsPanel.style.display = "none";
                    updateFixedHorizons();
                }
            });

            elements.modeContinuous.addEventListener("change", () => {
                if (elements.modeContinuous.checked) {
                    state.horizonMode = "continuous";
                    if (elements.fixedHorizonsPanel) elements.fixedHorizonsPanel.style.display = "none";
                    if (elements.continuousHorizonsPanel) elements.continuousHorizonsPanel.style.display = "block";
                    updateContinuousHorizons();
                }
            });
        }

        // Fixed Horizon Chips
        const horizonChips = document.querySelectorAll("#horizons-chips-container .chip-btn");
        horizonChips.forEach(chip => {
            chip.addEventListener("click", () => {
                chip.classList.toggle("active");
                updateFixedHorizons();
            });
        });

        // Continuous Daily Range Chips (1-7, 1-15, 1-30, 1-60, 1-90)
        const continuousChips = document.querySelectorAll("#continuous-chips-container .chip-btn");
        continuousChips.forEach(chip => {
            chip.addEventListener("click", () => {
                continuousChips.forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                state.selectedRangeKey = chip.getAttribute("data-range");
                updateContinuousHorizons();
            });
        });

        // Ratio Chips
        const ratioChips = document.querySelectorAll("#ratios-chips-container .chip-btn");
        ratioChips.forEach(chip => {
            chip.addEventListener("click", () => {
                chip.classList.toggle("active");
                const activeRatios = Array.from(document.querySelectorAll("#ratios-chips-container .chip-btn.active"))
                    .map(c => c.getAttribute("data-ratio"));
                state.selectedRatios = activeRatios;
            });
        });
    }

    function updateFixedHorizons() {
        const activeHorizons = Array.from(document.querySelectorAll("#horizons-chips-container .chip-btn.active"))
            .map(c => parseInt(c.getAttribute("data-horizon")));
        state.selectedHorizons = activeHorizons;
    }

    function updateContinuousHorizons() {
        const rangeKey = state.selectedRangeKey || "1-7";
        state.selectedHorizons = state.continuousRanges[rangeKey] || Array.from({ length: 7 }, (_, i) => i + 1);
    }

    function populateModelFilterOptions(models) {
        if (!elements.filterModelSelect) return;
        const currentVal = elements.filterModelSelect.value;
        elements.filterModelSelect.innerHTML = '<option value="ALL">All Models</option>';
        models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            elements.filterModelSelect.appendChild(opt);
        });
        elements.filterModelSelect.value = currentVal && models.includes(currentVal) ? currentVal : "ALL";
    }

    function populateHorizonFilterOptions(cards) {
        if (!elements.filterHorizonSelect) return;
        const currentVal = elements.filterHorizonSelect.value;
        elements.filterHorizonSelect.innerHTML = '<option value="ALL">All Horizons</option>';
        
        // Extract unique horizons in sorted order
        const uniqueHorizons = Array.from(new Set(cards.map(c => c.horizon))).sort((a, b) => a - b);
        uniqueHorizons.forEach(h => {
            const opt = document.createElement("option");
            opt.value = String(h);
            opt.textContent = `Day ${h}${h > 1 ? ` (${h} Days)` : ''}`;
            elements.filterHorizonSelect.appendChild(opt);
        });
        elements.filterHorizonSelect.value = currentVal && uniqueHorizons.map(String).includes(currentVal) ? currentVal : "ALL";
    }

    // =========================================================================
    // 4. Execution & SSE Streaming Handler
    // =========================================================================

    function setupEventListeners() {
        if (elements.btnRunForecast) {
            elements.btnRunForecast.addEventListener("click", runForecast);
        }

        if (elements.btnStopForecast) {
            elements.btnStopForecast.addEventListener("click", stopForecast);
        }

        if (elements.btnRefreshData) {
            elements.btnRefreshData.addEventListener("click", async () => {
                await fetchMarketSummary();
                await fetchHistoricalData(180);
            });
        }

        // CSV Upload Handler
        if (elements.fileCsvUpload) {
            elements.fileCsvUpload.addEventListener("change", async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append("file", file);
                try {
                    const res = await fetch("/api/data/upload", { method: "POST", body: formData });
                    const json = await res.json();
                    if (json.status === "success") {
                        alert(`Success: ${json.message}`);
                        await fetchMarketSummary();
                        await fetchHistoricalData(180);
                    } else {
                        alert(`Error: ${json.detail || "Upload failed"}`);
                    }
                } catch (err) {
                    alert(`Upload error: ${err.message}`);
                }
            });
        }

        // Visualizer Mode Tabs (Forecast vs Actual vs Historical Overview)
        if (elements.tabModeForecast) {
            elements.tabModeForecast.addEventListener("click", () => {
                state.chartMode = "forecast";
                updateMainVisualizer();
            });
        }
        if (elements.tabModeHistorical) {
            elements.tabModeHistorical.addEventListener("click", () => {
                state.chartMode = "historical";
                updateMainVisualizer();
            });
        }

        // Chart Model Selector
        if (elements.chartModelSelect) {
            elements.chartModelSelect.addEventListener("change", (e) => {
                state.chartSelectedModel = e.target.value;
                state.chartSelectedRatio = "ALL";
                state.chartSelectedMetric = "ALL";
                updateMainVisualizer();
            });
        }

        // Chart Ratio Selector
        if (elements.chartRatioSelect) {
            elements.chartRatioSelect.addEventListener("change", (e) => {
                state.chartSelectedRatio = e.target.value;
                updateMainVisualizer();
            });
        }

        // Chart Optimization Metric Selector
        if (elements.chartOptMetricSelect) {
            elements.chartOptMetricSelect.addEventListener("change", (e) => {
                state.chartSelectedMetric = e.target.value;
                updateMainVisualizer();
            });
        }

        // Metric View Category Tabs
        const metricTabPills = document.querySelectorAll(".metric-tab-pill");
        metricTabPills.forEach(pill => {
            pill.addEventListener("click", () => {
                metricTabPills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                state.metricFilterCategory = pill.getAttribute("data-view");
                if (state.currentComparisonMetrics) {
                    renderComparisonMetricsPanel(state.currentComparisonMetrics);
                }
            });
        });

        // Focus Metric Selector
        if (elements.metricSingleSelect) {
            elements.metricSingleSelect.addEventListener("change", (e) => {
                state.metricFilterSingle = e.target.value;
                if (state.currentComparisonMetrics) {
                    renderComparisonMetricsPanel(state.currentComparisonMetrics);
                }
            });
        }

        // Performance Tier Filter
        if (elements.metricGradeSelect) {
            elements.metricGradeSelect.addEventListener("change", (e) => {
                state.metricFilterGrade = e.target.value;
                if (state.currentComparisonMetrics) {
                    renderComparisonMetricsPanel(state.currentComparisonMetrics);
                }
            });
        }

        // Range Slice Buttons (ALL, 7D, 15D, 30D, 60D, 90D)
        const rangeSliceBtns = document.querySelectorAll(".range-slice-btn");
        rangeSliceBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                rangeSliceBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                state.chartHorizonSlice = btn.getAttribute("data-slice");
                updateMainVisualizer();
            });
        });

        // Timeframe Buttons (Historical Overview Mode)
        const timeframeBtns = document.querySelectorAll(".timeframe-btn");
        timeframeBtns.forEach(btn => {
            btn.addEventListener("click", async () => {
                timeframeBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const period = parseInt(btn.getAttribute("data-period"));
                await fetchHistoricalData(period);
            });
        });

        // Zoom Controls
        if (elements.btnZoomIn) {
            elements.btnZoomIn.addEventListener("click", () => {
                // Zoom in to 7D or next tighter slice
                if (state.chartHorizonSlice === "ALL") state.chartHorizonSlice = "30";
                else if (state.chartHorizonSlice === "90") state.chartHorizonSlice = "60";
                else if (state.chartHorizonSlice === "60") state.chartHorizonSlice = "30";
                else if (state.chartHorizonSlice === "30") state.chartHorizonSlice = "15";
                else if (state.chartHorizonSlice === "15") state.chartHorizonSlice = "7";
                
                rangeSliceBtns.forEach(b => {
                    if (b.getAttribute("data-slice") === state.chartHorizonSlice) b.classList.add("active");
                    else b.classList.remove("active");
                });
                updateMainVisualizer();
            });
        }

        if (elements.btnZoomOut) {
            elements.btnZoomOut.addEventListener("click", () => {
                if (state.chartHorizonSlice === "7") state.chartHorizonSlice = "15";
                else if (state.chartHorizonSlice === "15") state.chartHorizonSlice = "30";
                else if (state.chartHorizonSlice === "30") state.chartHorizonSlice = "60";
                else if (state.chartHorizonSlice === "60") state.chartHorizonSlice = "90";
                else if (state.chartHorizonSlice === "90") state.chartHorizonSlice = "ALL";
                
                rangeSliceBtns.forEach(b => {
                    if (b.getAttribute("data-slice") === state.chartHorizonSlice) b.classList.add("active");
                    else b.classList.remove("active");
                });
                updateMainVisualizer();
            });
        }

        if (elements.btnZoomReset) {
            elements.btnZoomReset.addEventListener("click", () => {
                state.chartHorizonSlice = "ALL";
                rangeSliceBtns.forEach(b => {
                    if (b.getAttribute("data-slice") === "ALL") b.classList.add("active");
                    else b.classList.remove("active");
                });
                updateMainVisualizer();
            });
        }

        // Fullscreen / Expand Button
        if (elements.btnChartExpand) {
            elements.btnChartExpand.addEventListener("click", () => {
                const card = elements.mainVisualizerCard;
                if (!card) return;
                const isFullscreen = card.classList.toggle("fullscreen-chart-mode");
                if (elements.btnExpandText) {
                    elements.btnExpandText.textContent = isFullscreen ? "⛶ Exit Fullscreen" : "⛶ Expand";
                }
                setTimeout(() => {
                    if (state.chartInstance) state.chartInstance.resize();
                }, 100);
            });
        }

        // Drawer Comparison Table Toggle
        if (elements.btnToggleCompTable) {
            elements.btnToggleCompTable.addEventListener("click", () => {
                const content = elements.compTableDrawerContent;
                if (!content) return;
                const isHidden = content.style.display === "none";
                content.style.display = isHidden ? "block" : "none";
                if (elements.drawerToggleText) {
                    elements.drawerToggleText.textContent = isHidden ? "Hide Detailed Forecast vs Actual Comparison Table ▲" : "Show Detailed Forecast vs Actual Comparison Table ▼";
                }
            });
        }

        // Filter Handlers
        if (elements.filterHorizonSelect) {
            elements.filterHorizonSelect.addEventListener("change", renderFilteredResults);
        }
        if (elements.filterModelSelect) {
            elements.filterModelSelect.addEventListener("change", renderFilteredResults);
        }

        // Single Global Actual Data Upload Handler
        if (elements.globalActualUpload) {
            elements.globalActualUpload.addEventListener("change", async (e) => {
                const file = e.target.files[0];
                if (file) {
                    await handleActualDataUpload(file);
                    e.target.value = "";
                }
            });
        }

        // Chart Actual Data Upload Handler
        if (elements.chartActualUpload) {
            elements.chartActualUpload.addEventListener("change", async (e) => {
                const file = e.target.files[0];
                if (file) {
                    await handleActualDataUpload(file);
                    e.target.value = "";
                }
            });
        }

        // Card Expand Modal Controls
        if (elements.btnCloseExpandModal) {
            elements.btnCloseExpandModal.addEventListener("click", closeCardExpandModal);
        }

        if (elements.cardExpandModal) {
            elements.cardExpandModal.addEventListener("click", (e) => {
                if (e.target === elements.cardExpandModal) {
                    closeCardExpandModal();
                }
            });
        }

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && elements.cardExpandModal && elements.cardExpandModal.style.display !== "none") {
                closeCardExpandModal();
            }
        });

        if (elements.modalBtnZoomIn) {
            elements.modalBtnZoomIn.addEventListener("click", () => {
                if (!state.activeExpandedCard) return;
                const curr = state.activeExpandedCard.zoomSlice;
                if (curr === "ALL") state.activeExpandedCard.zoomSlice = "30";
                else if (curr === "90") state.activeExpandedCard.zoomSlice = "60";
                else if (curr === "60") state.activeExpandedCard.zoomSlice = "30";
                else if (curr === "30") state.activeExpandedCard.zoomSlice = "15";
                else if (curr === "15") state.activeExpandedCard.zoomSlice = "7";
                renderCardExpandModalContent();
            });
        }

        if (elements.modalBtnZoomOut) {
            elements.modalBtnZoomOut.addEventListener("click", () => {
                if (!state.activeExpandedCard) return;
                const curr = state.activeExpandedCard.zoomSlice;
                if (curr === "7") state.activeExpandedCard.zoomSlice = "15";
                else if (curr === "15") state.activeExpandedCard.zoomSlice = "30";
                else if (curr === "30") state.activeExpandedCard.zoomSlice = "60";
                else if (curr === "60") state.activeExpandedCard.zoomSlice = "90";
                else if (curr === "90") state.activeExpandedCard.zoomSlice = "ALL";
                renderCardExpandModalContent();
            });
        }

        if (elements.modalBtnZoomReset) {
            elements.modalBtnZoomReset.addEventListener("click", () => {
                if (!state.activeExpandedCard) return;
                state.activeExpandedCard.zoomSlice = "ALL";
                renderCardExpandModalContent();
            });
        }

        // View Switch Handlers
        if (elements.btnViewCards && elements.btnViewMatrix) {
            elements.btnViewCards.addEventListener("click", () => {
                elements.btnViewCards.classList.add("active");
                elements.btnViewMatrix.classList.remove("active");
                if (elements.resultsGridContainer) elements.resultsGridContainer.style.display = "block";
                if (elements.resultMatrixContainer) elements.resultMatrixContainer.style.display = "none";
            });

            elements.btnViewMatrix.addEventListener("click", () => {
                elements.btnViewMatrix.classList.add("active");
                elements.btnViewCards.classList.remove("active");
                if (elements.resultsGridContainer) elements.resultsGridContainer.style.display = "none";
                if (elements.resultMatrixContainer) elements.resultMatrixContainer.style.display = "block";
            });
        }

        // Pagination Handlers
        if (elements.gridPageSizeSelect) {
            elements.gridPageSizeSelect.addEventListener("change", (e) => {
                state.pageSize = e.target.value;
                state.currentPage = 1;
                renderResultsGridPage();
            });
        }

        if (elements.btnPagFirst) {
            elements.btnPagFirst.addEventListener("click", () => {
                state.currentPage = 1;
                renderResultsGridPage();
            });
        }

        if (elements.btnPagPrev) {
            elements.btnPagPrev.addEventListener("click", () => {
                if (state.currentPage > 1) {
                    state.currentPage--;
                    renderResultsGridPage();
                }
            });
        }

        if (elements.btnPagNext) {
            elements.btnPagNext.addEventListener("click", () => {
                const totalPages = calculateTotalPages();
                if (state.currentPage < totalPages) {
                    state.currentPage++;
                    renderResultsGridPage();
                }
            });
        }

        if (elements.btnPagLast) {
            elements.btnPagLast.addEventListener("click", () => {
                state.currentPage = calculateTotalPages();
                renderResultsGridPage();
            });
        }

        // Export Handlers
        if (elements.btnExportCsv) {
            elements.btnExportCsv.addEventListener("click", exportResultsToCSV);
        }
        if (elements.btnExportJson) {
            elements.btnExportJson.addEventListener("click", exportResultsToJSON);
        }
    }

    async function runForecast() {
        if (state.selectedModels.length === 0) {
            alert("Please select at least one model.");
            return;
        }
        if (state.selectedMetrics.length === 0) {
            alert("Please select at least one error metric.");
            return;
        }
        if (state.selectedHorizons.length === 0) {
            alert("Please select at least one forecast horizon.");
            return;
        }
        if (state.selectedRatios.length === 0) {
            alert("Please select at least one train/test ratio.");
            return;
        }

        // UI State -> Running
        elements.btnRunForecast.style.display = "none";
        elements.btnStopForecast.style.display = "inline-flex";
        elements.progressContainer.style.display = "block";
        elements.resultsEmptyPlaceholder.style.display = "none";
        if (elements.resultsGridContainer) elements.resultsGridContainer.style.display = "block";
        if (elements.resultsGridBody) elements.resultsGridBody.innerHTML = "";
        if (elements.matrixTableBody) elements.matrixTableBody.innerHTML = "";
        state.results = [];
        state.currentFilteredResults = [];

        try {
            const payload = {
                models: state.selectedModels,
                metrics: state.selectedMetrics,
                horizons: state.selectedHorizons,
                ratios: state.selectedRatios,
                auto_tuning: state.autoTuning
            };

            const res = await fetch("/api/forecast/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const json = await res.json();
            if (json.status === "started") {
                state.activeJobId = json.job_id;
                startSSEProgressStream(json.job_id);
            }
        } catch (err) {
            console.error("Run forecast error:", err);
            alert("Failed to start forecast engine.");
            resetRunButtons();
        }
    }

    function startSSEProgressStream(jobId) {
        if (state.eventSource) {
            state.eventSource.close();
        }

        state.eventSource = new EventSource(`/api/forecast/stream/${jobId}`);

        state.eventSource.onmessage = async (e) => {
            const data = JSON.parse(e.data);
            updateProgressUI(data);

            if (data.status === "COMPLETED" || data.status === "ERROR" || data.status === "CANCELLED") {
                state.eventSource.close();
                state.eventSource = null;
                resetRunButtons();
                
                if (data.status === "COMPLETED") {
                    await fetchAndRenderFinalResults(jobId);
                } else if (data.status === "ERROR") {
                    alert(`Execution Error: ${data.error}`);
                }
            }
        };

        state.eventSource.onerror = () => {
            // Fallback polling if SSE disconnects
            pollJobStatus(jobId);
        };
    }

    async function pollJobStatus(jobId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/forecast/status/${jobId}`);
                const data = await res.json();
                updateProgressUI(data);
                if (data.status === "COMPLETED" || data.status === "ERROR" || data.status === "CANCELLED") {
                    clearInterval(interval);
                    resetRunButtons();
                    if (data.status === "COMPLETED") {
                        await fetchAndRenderFinalResults(jobId);
                    }
                }
            } catch (err) {
                clearInterval(interval);
                resetRunButtons();
            }
        }, 800);
    }

    function updateProgressUI(data) {
        if (elements.progressBarInner) elements.progressBarInner.style.width = `${data.progress}%`;
        if (elements.progPctText) elements.progPctText.textContent = `${data.progress.toFixed(1)}%`;
        if (elements.progressExpCounter) elements.progressExpCounter.textContent = `Completed: ${data.completed} / ${data.total} Experiments`;
        if (elements.progCurrentModel) elements.progCurrentModel.textContent = data.current_model || "--";
        if (elements.progCurrentHorizon) elements.progCurrentHorizon.textContent = data.current_horizon || "--";
        if (elements.progCurrentRatio) elements.progCurrentRatio.textContent = data.current_ratio || "--";
        if (elements.progCurrentMetric) elements.progCurrentMetric.textContent = data.current_metric || "--";
    }

    async function fetchAndRenderFinalResults(jobId) {
        try {
            const res = await fetch(`/api/forecast/results/${jobId}`);
            const json = await res.json();
            if (json.results) {
                state.results = json.results;
                if (elements.resultsCountBadge) {
                    elements.resultsCountBadge.textContent = `${json.results.length} Experiment Cards`;
                }
                populateHorizonFilterOptions(json.results);
                renderFilteredResults();
                state.chartMode = "forecast";
                updateMainVisualizer();
            }
        } catch (err) {
            console.error("Failed to fetch results:", err);
        }
    }

    async function stopForecast() {
        if (state.activeJobId) {
            await fetch(`/api/forecast/cancel/${state.activeJobId}`, { method: "POST" });
            if (state.eventSource) state.eventSource.close();
            resetRunButtons();
        }
    }

    function resetRunButtons() {
        if (elements.btnRunForecast) elements.btnRunForecast.style.display = "inline-flex";
        if (elements.btnStopForecast) elements.btnStopForecast.style.display = "none";
    }

    // =========================================================================
    // 5. Result Data Grid & Comparison Matrix Rendering with Pagination
    // =========================================================================

    function calculateTotalPages() {
        const total = state.currentFilteredResults.length;
        if (total === 0) return 1;
        if (state.pageSize === "ALL") return 1;
        const size = parseInt(state.pageSize) || 25;
        return Math.max(1, Math.ceil(total / size));
    }

    function renderFilteredResults() {
        const horizonFilter = elements.filterHorizonSelect ? elements.filterHorizonSelect.value : "ALL";
        const modelFilter = elements.filterModelSelect ? elements.filterModelSelect.value : "ALL";

        let filtered = state.results;
        if (horizonFilter !== "ALL") {
            filtered = filtered.filter(r => String(r.horizon) === horizonFilter);
        }
        if (modelFilter !== "ALL") {
            filtered = filtered.filter(r => r.model === modelFilter);
        }

        state.currentFilteredResults = filtered;
        state.currentPage = 1;

        if (elements.resultsCountBadge) {
            elements.resultsCountBadge.textContent = `${filtered.length} Forecast Records (of ${state.results.length})`;
        }

        renderResultsGridPage();
        renderMatrixTable(filtered);
    }

    function renderResultsGridPage() {
        if (!elements.resultsGridBody) return;
        elements.resultsGridBody.innerHTML = "";

        const total = state.currentFilteredResults.length;

        if (total === 0) {
            elements.resultsGridBody.innerHTML = `
                <tr>
                    <td colspan="17" class="grid-empty-cell">
                        <div class="empty-state-box" style="padding: 30px 20px; border: none; background: transparent;">
                            <h3 style="font-size: 14px; margin-bottom: 4px;">No matching forecast results found</h3>
                            <p style="font-size: 12px;">Try adjusting your horizon or model filter settings above.</p>
                        </div>
                    </td>
                </tr>
            `;
            updatePaginationUI(0, 0, 0, 1, 1);
            return;
        }

        const pageSize = state.pageSize === "ALL" ? total : parseInt(state.pageSize) || 25;
        const totalPages = Math.max(1, Math.ceil(total / pageSize));

        if (state.currentPage > totalPages) state.currentPage = totalPages;
        if (state.currentPage < 1) state.currentPage = 1;

        const startIdx = (state.currentPage - 1) * pageSize;
        const endIdx = Math.min(startIdx + pageSize, total);
        const pageRecords = state.currentFilteredResults.slice(startIdx, endIdx);

        const actualMap = new Map((state.uploadedActualData || []).map(r => [r.date, r.actual_close]));

        pageRecords.forEach((c, i) => {
            const rowIndex = startIdx + i;
            const isPos = c.price_change >= 0;
            const changeSign = isPos ? "+" : "";

            // Format Best Params if Auto Tuned
            let bestParamsText = "Default Preset";
            if (c.auto_tuned === "Yes" && c.best_params && Object.keys(c.best_params).length > 0) {
                bestParamsText = Object.entries(c.best_params).map(([k, v]) => `${k}=${v}`).join(", ");
            }

            // Actual data matching evaluation for this single record
            const hasActual = actualMap.has(c.target_date);
            let actualPriceHtml = `<span class="col-pending">—</span>`;
            let diffHtml = `<span class="col-pending">—</span>`;
            let errPctHtml = `<span class="col-pending">—</span>`;
            let dirMatchHtml = `<span class="col-pending">—</span>`;

            if (hasActual) {
                const actPrice = Number(actualMap.get(c.target_date));
                const predPrice = Number(c.predicted_price);
                const diff = predPrice - actPrice;
                const errPct = (Math.abs(diff) / actPrice) * 100;
                const origin = c.latest_price || predPrice;
                const matchDir = Math.sign(predPrice - origin) === Math.sign(actPrice - origin);

                actualPriceHtml = `<span class="col-actual-price font-mono font-bold">$${actPrice.toFixed(4)}</span>`;
                diffHtml = `<span class="diff-badge ${Math.abs(diff) < 0.05 ? 'positive' : (diff > 0 ? 'positive' : 'negative')}">${diff >= 0 ? '+' : ''}$${diff.toFixed(4)}</span>`;
                errPctHtml = `<span class="font-mono font-bold">${errPct.toFixed(2)}%</span>`;
                dirMatchHtml = matchDir 
                    ? `<span class="diff-badge positive">✓ MATCHED</span>` 
                    : `<span class="diff-badge negative">✗ DIVERGED</span>`;
            } else if (state.uploadedActualData && state.uploadedActualData.length > 0) {
                actualPriceHtml = `<span class="col-pending" title="Date ${c.target_date} not found in uploaded file">No Date</span>`;
            }

            const tr = document.createElement("tr");
            tr.className = "results-grid-row";
            tr.innerHTML = `
                <td class="col-num">${rowIndex + 1}</td>
                <td><span class="grid-model-pill">${c.model}</span></td>
                <td><span class="horizon-tag">${c.horizon_label || `${c.horizon}D`}</span></td>
                <td><span class="ratio-tag">${c.ratio}</span></td>
                <td class="col-date">${c.target_date}</td>
                <td class="col-price">$${Number(c.predicted_price).toFixed(4)}</td>
                <td>
                    <span class="diff-badge ${isPos ? "positive" : "negative"}">
                        ${changeSign}$${Number(c.price_change).toFixed(4)} (${changeSign}${Number(c.price_change_pct).toFixed(2)}%)
                    </span>
                </td>
                <td>
                    <span class="grid-opt-metric" title="Optimized Error Metric">
                        <span class="lbl">${c.metric_name}:</span> <strong class="val">${c.metric_score}</strong>
                    </span>
                </td>
                <td>${actualPriceHtml}</td>
                <td>${diffHtml}</td>
                <td>${errPctHtml}</td>
                <td>${dirMatchHtml}</td>
                <td class="col-mono">${c.all_metrics?.MAE !== undefined ? c.all_metrics.MAE : "--"}</td>
                <td class="col-mono">${c.all_metrics?.RMSE !== undefined ? c.all_metrics.RMSE : "--"}</td>
                <td class="col-mono">${c.all_metrics?.MAPE !== undefined ? `${c.all_metrics.MAPE}%` : "--"}</td>
                <td class="col-mono">${c.all_metrics?.["R²"] !== undefined ? c.all_metrics["R²"] : "--"}</td>
                <td class="col-mono text-green font-bold">${c.all_metrics?.["Directional Accuracy"] !== undefined ? `${c.all_metrics["Directional Accuracy"]}%` : "--"}</td>
                <td><span class="grid-leakage-badge" title="Purged Chronological Partition Certified">🛡️ ${c.leakage_check}</span></td>
                <td>
                    ${c.auto_tuned === "Yes" 
                        ? `<span class="grid-tune-tag tuned" title="${bestParamsText.replace(/"/g, '&quot;')}">Auto-Tuned</span>` 
                        : `<span class="grid-tune-tag preset">Preset</span>`
                    }
                </td>
                <td style="text-align: center;">
                    <button type="button" class="btn-grid-chart-action" data-row-idx="${rowIndex}" title="Open Full Screen Interactive Chart & Comparison Analysis">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                        <span>Chart</span>
                    </button>
                </td>
            `;

            elements.resultsGridBody.appendChild(tr);
        });

        // Setup Chart Action Click Listeners
        document.querySelectorAll(".btn-grid-chart-action").forEach(btn => {
            btn.addEventListener("click", () => {
                const rIdx = parseInt(btn.getAttribute("data-row-idx"));
                const targetCard = state.currentFilteredResults[rIdx];
                if (targetCard) {
                    const globalIdx = state.results.indexOf(targetCard);
                    openCardExpandModal(targetCard, globalIdx >= 0 ? globalIdx : rIdx);
                }
            });
        });

        updatePaginationUI(startIdx + 1, endIdx, total, state.currentPage, totalPages);
    }

    function updatePaginationUI(start, end, total, page, totalPages) {
        if (elements.pagStart) elements.pagStart.textContent = total === 0 ? 0 : start;
        if (elements.pagEnd) elements.pagEnd.textContent = end;
        if (elements.pagTotal) elements.pagTotal.textContent = total;
        if (elements.pagCurrentPage) elements.pagCurrentPage.textContent = page;
        if (elements.pagTotalPages) elements.pagTotalPages.textContent = totalPages;

        if (elements.btnPagFirst) elements.btnPagFirst.disabled = page <= 1;
        if (elements.btnPagPrev) elements.btnPagPrev.disabled = page <= 1;
        if (elements.btnPagNext) elements.btnPagNext.disabled = page >= totalPages;
        if (elements.btnPagLast) elements.btnPagLast.disabled = page >= totalPages;
    }

    // =========================================================================
    // Single Global Actual Data Upload & Evaluation Metrics Engine
    // =========================================================================

    async function handleActualDataUpload(file) {
        if (!file) return;
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/forecast/upload-actual", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (!res.ok) {
                alert(`Upload error: ${data.detail || "Failed to process actual data"}`);
                return;
            }

            if (data.records && data.records.length > 0) {
                state.uploadedActualData = data.records;
                state.uploadedActualFilename = data.filename || file.name;

                // Update Single Global Upload Button & Badge
                if (elements.globalUploadBtnText) {
                    elements.globalUploadBtnText.textContent = "📁 Replace Actual Data";
                }
                if (elements.globalUploadStatusBadge) {
                    elements.globalUploadStatusBadge.style.display = "inline-flex";
                    elements.globalUploadStatusBadge.textContent = `📄 ${state.uploadedActualFilename} (${data.records.length} records loaded)`;
                }

                // Automatically apply to ALL model cards across all horizons
                renderFilteredResults();

                // Automatically update top visualizer
                updateMainVisualizer();

                // If a card is currently expanded in the modal, automatically refresh it
                if (state.activeExpandedCard) {
                    renderCardExpandModalContent();
                }
            }
        } catch (err) {
            console.error("Failed to upload actual data:", err);
            alert(`Error uploading file: ${err.message}`);
        }
    }

    function calculateComparisonMetrics(matchedPairs, originPrice) {
        if (!matchedPairs || matchedPairs.length === 0) return null;
        const n = matchedPairs.length;
        const preds = matchedPairs.map(p => p.pred);
        const actuals = matchedPairs.map(p => p.actual);

        const errors = preds.map((p, i) => p - actuals[i]);
        const absErrors = errors.map(Math.abs);
        const sqErrors = errors.map(e => e * e);

        const mae = absErrors.reduce((a, b) => a + b, 0) / n;
        const rmse = Math.sqrt(sqErrors.reduce((a, b) => a + b, 0) / n);

        const mape = (actuals.reduce((sum, a, i) => sum + (Math.abs(preds[i] - a) / (a + 1e-8)), 0) / n) * 100;
        const smape = (actuals.reduce((sum, a, i) => sum + (Math.abs(preds[i] - a) / ((Math.abs(a) + Math.abs(preds[i])) / 2 + 1e-8)), 0) / n) * 100;

        const meanActual = actuals.reduce((a, b) => a + b, 0) / n;
        const ssTot = actuals.reduce((sum, a) => sum + Math.pow(a - meanActual, 2), 0);
        const ssRes = sqErrors.reduce((a, b) => a + b, 0);
        const r2 = ssTot === 0 ? 0 : 1 - (ssRes / ssTot);

        const meanError = errors.reduce((a, b) => a + b, 0) / n;
        const maxAbsError = Math.max(...absErrors);

        const variance = errors.reduce((sum, e) => sum + Math.pow(e - meanError, 2), 0) / (n > 1 ? n - 1 : 1);
        const errorStdDev = Math.sqrt(variance);

        const origin = originPrice !== undefined ? originPrice : actuals[0];
        const correctDirs = actuals.map((a, i) => Math.sign(a - origin) === Math.sign(preds[i] - origin));
        const dirAcc = (correctDirs.filter(Boolean).length / n) * 100;

        const upActuals = actuals.map((a, i) => ({ a, p: preds[i], up: a > origin }));
        const ups = upActuals.filter(x => x.up);
        const upAcc = ups.length > 0 ? (ups.filter(x => x.p > origin).length / ups.length) * 100 : 100;

        const downs = upActuals.filter(x => !x.up);
        const downAcc = downs.length > 0 ? (downs.filter(x => x.p < origin).length / downs.length) * 100 : 100;

        return {
            "MAE": Number(mae.toFixed(4)),
            "RMSE": Number(rmse.toFixed(4)),
            "MAPE": Number(mape.toFixed(2)),
            "sMAPE": Number(smape.toFixed(2)),
            "R²": Number(r2.toFixed(4)),
            "Mean Error (Bias)": Number(meanError.toFixed(4)),
            "Directional Accuracy": Number(dirAcc.toFixed(1)),
            "UP Accuracy": Number(upAcc.toFixed(1)),
            "DOWN Accuracy": Number(downAcc.toFixed(1)),
            "Max Absolute Error": Number(maxAbsError.toFixed(4)),
            "Error Std Dev": Number(errorStdDev.toFixed(4))
        };
    }

    // =========================================================================
    // 6. Dedicated Result Expansion Modal Engine
    // =========================================================================

    function openCardExpandModal(c, idx) {
        if (!elements.cardExpandModal) return;

        // Gather all sequence points for this card's model & ratio up to this horizon
        const allSequence = state.results
            .filter(r => r.model === c.model && r.ratio === c.ratio)
            .sort((a, b) => a.horizon - b.horizon);
        
        let targetSeq = allSequence.filter(r => r.horizon <= c.horizon);
        if (targetSeq.length === 0) targetSeq = allSequence.length > 0 ? allSequence : [c];

        state.activeExpandedCard = {
            card: c,
            cardIdx: idx,
            targetSeq: targetSeq,
            zoomSlice: "ALL"
        };

        renderCardExpandModalContent();
        elements.cardExpandModal.style.display = "flex";
        document.body.style.overflow = "hidden";
    }

    function closeCardExpandModal() {
        if (!elements.cardExpandModal) return;
        elements.cardExpandModal.style.display = "none";
        document.body.style.overflow = "";
        if (state.modalChartInstance) {
            state.modalChartInstance.destroy();
            state.modalChartInstance = null;
        }
        state.activeExpandedCard = null;
    }

    function renderCardExpandModalContent() {
        if (!state.activeExpandedCard) return;
        const { card, targetSeq, zoomSlice } = state.activeExpandedCard;

        // Update Modal Header
        if (elements.modalModelName) elements.modalModelName.textContent = card.model;
        if (elements.modalHorizonLabel) elements.modalHorizonLabel.textContent = `${card.horizon_label} (${targetSeq.length} Day Horizon)`;
        if (elements.modalRatioLabel) elements.modalRatioLabel.textContent = `Ratio: ${card.ratio}`;
        if (elements.modalLeakageBadge) elements.modalLeakageBadge.textContent = `🛡️ ZERO LEAKAGE CERTIFIED`;
        if (elements.modalTargetMeta) {
            elements.modalTargetMeta.textContent = `Target Horizon End: ${card.target_date} | Baseline Session Price: $${Number(card.latest_price).toFixed(4)} | Optimized: ${card.metric_name}`;
        }

        // Apply slice if Zoom is active
        let visibleSequence = [...targetSeq];
        if (zoomSlice !== "ALL") {
            const limit = parseInt(zoomSlice);
            if (!isNaN(limit)) visibleSequence = targetSeq.slice(0, limit);
        }

        const actualMap = new Map((state.uploadedActualData || []).map(r => [r.date, r.actual_close]));
        const labels = visibleSequence.map(s => s.target_date);
        const predPrices = visibleSequence.map(s => Number(s.predicted_price));
        const actualPrices = visibleSequence.map(s => actualMap.has(s.target_date) ? Number(actualMap.get(s.target_date)) : null);

        const matchedPairs = [];
        visibleSequence.forEach(s => {
            if (actualMap.has(s.target_date)) {
                matchedPairs.push({ pred: Number(s.predicted_price), actual: Number(actualMap.get(s.target_date)) });
            }
        });

        // Top Hero Strip
        const endPred = Number(card.predicted_price);
        const endActual = actualMap.has(card.target_date) ? Number(actualMap.get(card.target_date)) : null;

        if (elements.modalPredPrice) elements.modalPredPrice.textContent = `$${endPred.toFixed(4)}`;
        if (elements.modalActualPrice) {
            elements.modalActualPrice.textContent = endActual !== null ? `$${endActual.toFixed(4)}` : "— Not Uploaded";
        }
        if (elements.modalDiffPrice) {
            if (endActual !== null) {
                const diff = endPred - endActual;
                const pct = (Math.abs(diff) / endActual) * 100;
                const sign = diff >= 0 ? "+" : "";
                elements.modalDiffPrice.textContent = `${sign}$${diff.toFixed(4)} (${pct.toFixed(2)}%)`;
                elements.modalDiffPrice.style.color = Math.abs(diff) < 0.05 ? "var(--accent-green)" : (diff > 0 ? "var(--accent-green)" : "var(--accent-red)");
            } else {
                elements.modalDiffPrice.textContent = "—";
                elements.modalDiffPrice.style.color = "#ffffff";
            }
        }
        if (elements.modalDirMatch) {
            if (endActual !== null) {
                const origin = card.latest_price || endPred;
                const match = Math.sign(endPred - origin) === Math.sign(endActual - origin);
                elements.modalDirMatch.textContent = match ? "✓ UP/DOWN Matched" : "✗ Direction Diverged";
                elements.modalDirMatch.className = `m-val ${match ? "green" : "red"}`;
            } else {
                elements.modalDirMatch.textContent = "— Pending";
                elements.modalDirMatch.className = "m-val";
            }
        }
        if (elements.modalMatchedCount) {
            elements.modalMatchedCount.textContent = `${matchedPairs.length} / ${visibleSequence.length} Days Matched`;
        }

        // Render Evaluation Metrics Grid (11 Metrics)
        if (elements.modalCompMetricsGrid) {
            if (matchedPairs.length > 0) {
                const compMetrics = calculateComparisonMetrics(matchedPairs, card.latest_price);
                if (compMetrics) {
                    elements.modalCompMetricsGrid.innerHTML = Object.entries(compMetrics).map(([mName, mVal]) => `
                        <div class="modal-metric-card">
                            <span class="lbl">${mName}</span>
                            <span class="val ${mName.includes("Accuracy") ? "green" : ""}">${typeof mVal === "number" && !mName.includes("Accuracy") && !mName.includes("MAPE") ? `$${mVal.toFixed(4)}` : mVal}</span>
                        </div>
                    `).join("");
                }
            } else {
                elements.modalCompMetricsGrid.innerHTML = `
                    <div style="grid-column: 1/-1; padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px; color: var(--text-muted); font-size: 11px; text-align: center;">
                        Upload actual market data via the <strong>[ 📁 Upload Actual Data ]</strong> button at the top to compute all 11 ground-truth evaluation metrics.
                    </div>
                `;
            }
        }

        // Render Day-by-Day Table Body
        if (elements.modalCompTableBody) {
            elements.modalCompTableBody.innerHTML = visibleSequence.map((s, i) => {
                const act = actualMap.has(s.target_date) ? Number(actualMap.get(s.target_date)) : null;
                const pred = Number(s.predicted_price);
                let diffText = "— Pending";
                let diffClass = "neutral";
                let errPctText = "—";
                let dirText = "—";

                if (act !== null) {
                    const diff = pred - act;
                    const sign = diff >= 0 ? "+" : "";
                    diffText = `${sign}$${diff.toFixed(4)}`;
                    diffClass = Math.abs(diff) < 0.05 ? "positive" : (diff > 0 ? "positive" : "negative");
                    const errPct = (Math.abs(diff) / act) * 100;
                    errPctText = `${errPct.toFixed(2)}%`;

                    const origin = s.latest_price || pred;
                    const matchDir = Math.sign(pred - origin) === Math.sign(act - origin);
                    dirText = matchDir ? `<span style="color: var(--accent-green); font-weight: 700;">✓ MATCHED</span>` : `<span style="color: var(--accent-red); font-weight: 700;">✗ DIVERGED</span>`;
                }

                return `
                    <tr>
                        <td><strong>Day ${i + 1}</strong> (${s.horizon_label || `${s.horizon}D`})</td>
                        <td>${s.target_date}</td>
                        <td style="color: #06b6d4; font-weight: 700;">$${pred.toFixed(4)}</td>
                        <td style="color: ${act !== null ? "#f59e0b" : "var(--text-subtle)"}; font-weight: 700;">${act !== null ? `$${act.toFixed(4)}` : "— Pending"}</td>
                        <td><span class="diff-badge ${diffClass}">${diffText}</span></td>
                        <td>${errPctText}</td>
                        <td>${dirText}</td>
                    </tr>
                `;
            }).join("");
        }

        // Render Modal Chart
        if (!elements.modalExpandedChart) return;
        const ctx = elements.modalExpandedChart.getContext("2d");

        const allPrices = [...predPrices, ...actualPrices.filter(v => v !== null)];
        const minP = Math.min(...allPrices);
        const maxP = Math.max(...allPrices);
        const spread = (maxP - minP) || 0.1;
        const padding = spread * 0.18;
        const yMin = Number((minP - padding).toFixed(2));
        const yMax = Number((maxP + padding).toFixed(2));

        if (state.modalChartInstance) {
            state.modalChartInstance.destroy();
        }

        state.modalChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: `${card.model} Forecast ($/lb)`,
                        data: predPrices,
                        borderColor: "#06b6d4",
                        backgroundColor: "rgba(6, 182, 212, 0.12)",
                        borderWidth: 3.5,
                        pointStyle: "circle",
                        pointRadius: 6,
                        pointHoverRadius: 9,
                        pointBackgroundColor: "#06b6d4",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        fill: false,
                        tension: 0.1
                    },
                    ...(state.uploadedActualData && state.uploadedActualData.length > 0 ? [{
                        label: `Uploaded Actual Market Close ($/lb) ${state.uploadedActualFilename ? `(${state.uploadedActualFilename})` : ""}`,
                        data: actualPrices,
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.15)",
                        borderWidth: 3,
                        borderDash: [6, 4],
                        pointStyle: "rectRot",
                        pointRadius: 8,
                        pointHoverRadius: 11,
                        pointBackgroundColor: "#f59e0b",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        fill: false,
                        spanGaps: true,
                        tension: 0.1
                    }] : [])
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            color: "#e5e7eb",
                            font: { family: "Inter", size: 12, weight: 700 },
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: "#111827",
                        titleColor: "#38bdf8",
                        titleFont: { family: "Inter", size: 13, weight: 700 },
                        bodyColor: "#f3f4f6",
                        bodyFont: { family: "JetBrains Mono", size: 12 },
                        borderColor: "#06b6d4",
                        borderWidth: 1.5,
                        padding: 12,
                        callbacks: {
                            title: function(items) {
                                const idx = items[0].dataIndex;
                                return `📅 Date: ${labels[idx]} (Day ${idx + 1} of ${labels.length})`;
                            },
                            label: function(ctx) {
                                const idx = ctx.dataIndex;
                                const pred = predPrices[idx];
                                const act = actualPrices[idx];
                                if (ctx.datasetIndex === 0) {
                                    return `  Predicted Price: $${pred.toFixed(4)}`;
                                } else {
                                    if (act === null) return `  Actual Price: Not Uploaded`;
                                    const diff = pred - act;
                                    const pct = (Math.abs(diff) / act) * 100;
                                    const sign = diff >= 0 ? "+" : "";
                                    return [
                                        `  Actual Price:    $${act.toFixed(4)}`,
                                        `  Difference:      ${sign}$${diff.toFixed(4)} (${pct.toFixed(2)}%)`
                                    ];
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { family: "JetBrains Mono", size: 11, weight: 600 },
                            maxRotation: 45
                        }
                    },
                    y: {
                        min: yMin,
                        max: yMax,
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { family: "JetBrains Mono", size: 11 },
                            callback: v => `$${Number(v).toFixed(2)}`
                        }
                    }
                }
            }
        });
    }

    function renderMatrixTable(cards) {
        if (!elements.matrixTableBody) return;
        elements.matrixTableBody.innerHTML = "";

        const actualMap = new Map((state.uploadedActualData || []).map(r => [r.date, r.actual_close]));

        cards.forEach(c => {
            const hasActual = actualMap.has(c.target_date);
            let actualPriceHtml = `<span style="color: var(--text-subtle);">—</span>`;
            let diffHtml = `<span style="color: var(--text-subtle);">—</span>`;
            let errPctHtml = `<span style="color: var(--text-subtle);">—</span>`;
            let dirMatchHtml = `<span style="color: var(--text-subtle);">—</span>`;

            if (hasActual) {
                const actPrice = Number(actualMap.get(c.target_date));
                const predPrice = Number(c.predicted_price);
                const diff = predPrice - actPrice;
                const errPct = (Math.abs(diff) / actPrice) * 100;
                const origin = c.latest_price || predPrice;
                const matchDir = Math.sign(predPrice - origin) === Math.sign(actPrice - origin);

                actualPriceHtml = `<span style="color: #f59e0b; font-weight:700; font-family: var(--font-mono);">$${actPrice.toFixed(4)}</span>`;
                diffHtml = `<span class="diff-badge ${Math.abs(diff) < 0.05 ? 'positive' : (diff > 0 ? 'positive' : 'negative')}">${diff >= 0 ? '+' : ''}$${diff.toFixed(4)}</span>`;
                errPctHtml = `<span style="font-weight:700; font-family: var(--font-mono);">${errPct.toFixed(2)}%</span>`;
                dirMatchHtml = matchDir 
                    ? `<span class="diff-badge positive">✓ MATCHED</span>` 
                    : `<span class="diff-badge negative">✗ DIVERGED</span>`;
            } else if (state.uploadedActualData && state.uploadedActualData.length > 0) {
                actualPriceHtml = `<span style="color: var(--text-subtle);">No Date</span>`;
            }

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${c.model}</strong></td>
                <td><span class="horizon-tag">${c.horizon_label}</span></td>
                <td>${c.ratio}</td>
                <td><span style="color: var(--accent-gold); font-weight:700;">${c.metric_name} (${c.metric_score})</span></td>
                <td>${c.target_date}</td>
                <td style="color: #60a5fa; font-weight:700;">$${Number(c.predicted_price).toFixed(4)}</td>
                <td>${actualPriceHtml}</td>
                <td>${diffHtml}</td>
                <td>${errPctHtml}</td>
                <td>${dirMatchHtml}</td>
                <td>${c.all_metrics?.MAE !== undefined ? c.all_metrics.MAE : (c.all_metrics?.MAE || 0)}</td>
                <td>${c.all_metrics?.RMSE !== undefined ? c.all_metrics.RMSE : (c.all_metrics?.RMSE || 0)}</td>
                <td>${c.all_metrics?.MAPE !== undefined ? `${c.all_metrics.MAPE}%` : '0%'}</td>
                <td>${c.all_metrics?.["R²"] !== undefined ? c.all_metrics["R²"] : '0'}</td>
                <td style="color: var(--accent-green); font-weight:700;">${c.all_metrics?.["Directional Accuracy"] !== undefined ? `${c.all_metrics["Directional Accuracy"]}%` : '0%'}</td>
                <td><span class="badge-leakage-header" style="padding: 2px 6px; font-size:9px;">${c.leakage_check}</span></td>
            `;
            elements.matrixTableBody.appendChild(tr);
        });
    }

    function updateForecastChartWithResults(cards) {
        // Collect latest best forecasts across distinct horizons for visual trajectory
        const horizonBestMap = {};
        cards.forEach(c => {
            if (!horizonBestMap[c.horizon] || c.metric_score < horizonBestMap[c.horizon].metric_score) {
                horizonBestMap[c.horizon] = c;
            }
        });
        const forecastPoints = Object.values(horizonBestMap);
        renderChart(state.historicalData, forecastPoints);
    }

    // =========================================================================
    // 7. CSV & JSON Export Utilities
    // =========================================================================

    function exportResultsToCSV() {
        if (state.results.length === 0) {
            alert("No forecasting results available to export.");
            return;
        }

        const headers = ["Model", "Horizon", "Ratio", "Target Metric", "Metric Score", "Predicted Price", "Target Date", "Auto Tuned", "Leakage Check", "MAE", "RMSE", "MAPE", "sMAPE", "R2", "Directional Accuracy"];
        const rows = state.results.map(c => [
            c.model,
            c.horizon,
            c.ratio,
            c.metric_name,
            c.metric_score,
            c.predicted_price,
            c.target_date,
            c.auto_tuned,
            c.leakage_check,
            c.all_metrics.MAE,
            c.all_metrics.RMSE,
            c.all_metrics.MAPE,
            c.all_metrics.sMAPE,
            c.all_metrics["R²"],
            c.all_metrics["Directional Accuracy"]
        ]);

        let csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `copper_multi_horizon_forecast_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function exportResultsToJSON() {
        if (state.results.length === 0) {
            alert("No forecasting results available to export.");
            return;
        }

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(state.results, null, 2));
        const link = document.createElement("a");
        link.setAttribute("href", dataStr);
        link.setAttribute("download", `copper_multi_horizon_forecast_${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Run Initialization
    initApp();
});
