"""
FastAPI Server for Multi-Horizon Copper Forecasting System
Exposes market summary, historical time-series, streaming forecasting engine, and static dashboard.
"""

import os
import json
import uuid
import asyncio
import threading
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel

from data_manager import DataManager, FORECAST_HORIZONS, RATIOS_CONFIG
from metrics import ALL_METRICS
from models import MODEL_REGISTRY
from pipeline import ForecastingPipeline

app = FastAPI(title="Multi-Horizon Copper Price Forecasting System", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
DATA_FILE = "market_data.csv"
data_mgr = DataManager(DATA_FILE)
pipeline = ForecastingPipeline(data_mgr)

# Request Models
class ForecastRequest(PydanticBaseModel):
    models: Optional[List[str]] = None
    metrics: Optional[List[str]] = None
    horizons: Optional[List[int]] = None
    ratios: Optional[List[str]] = None
    auto_tuning: bool = False

@app.get("/api/market-summary")
async def get_market_summary():
    """Returns Yahoo Finance-style Copper Market Summary cards."""
    try:
        summary = data_mgr.get_market_summary()
        return {"status": "success", "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/historical-data")
async def get_historical_data(limit: int = 250):
    """Returns recent historical time series data for interactive charts."""
    try:
        df = data_mgr.raw_df
        if df is None:
            return {"status": "success", "data": []}
            
        recent = df.tail(limit).copy()
        records = []
        for _, row in recent.iterrows():
            date_str = pd_to_str(row.get("Date"))
            records.append({
                "date": date_str,
                "open": float(row.get("Copper_Open", 0.0)),
                "high": float(row.get("Copper_High", 0.0)),
                "low": float(row.get("Copper_Low", 0.0)),
                "close": float(row.get("Copper_Close", 0.0)),
                "volume": int(row.get("Copper_Volume", 0)),
                "lme_stocks": int(row.get("LME_Stocks", 0)),
                "crude_oil": float(row.get("Crude_Oil", 0.0)),
                "dxy": float(row.get("DXY_Index", 0.0)),
                "rate": float(row.get("Interest_Rate", 0.0)),
                "spread": float(row.get("Basis_Spread_3M_Cash", 0.0))
            })
        return {"status": "success", "data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def pd_to_str(val):
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)

from data_manager import DataManager, FORECAST_HORIZONS, FIXED_HORIZONS, CONTINUOUS_RANGES, RATIOS_CONFIG

@app.get("/api/config")
async def get_config():
    """Returns available models, metrics, horizons, ranges, and ratios."""
    return {
        "status": "success",
        "models": list(MODEL_REGISTRY.keys()),
        "metrics": ALL_METRICS,
        "fixed_horizons": FIXED_HORIZONS,
        "continuous_ranges": {
            "1 to 7 Days": CONTINUOUS_RANGES["1-7"],
            "1 to 15 Days": CONTINUOUS_RANGES["1-15"],
            "1 to 30 Days": CONTINUOUS_RANGES["1-30"],
            "1 to 60 Days": CONTINUOUS_RANGES["1-60"],
            "1 to 90 Days": CONTINUOUS_RANGES["1-90"]
        },
        "ratios": list(RATIOS_CONFIG.keys())
    }

@app.post("/api/forecast/run")
async def run_forecast(req: ForecastRequest, background_tasks: BackgroundTasks):
    """Starts the multi-horizon forecasting pipeline in background."""
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    
    models = req.models or list(MODEL_REGISTRY.keys())
    metrics = req.metrics or ["RMSE", "MAE"]
    horizons = req.horizons or FORECAST_HORIZONS
    ratios = req.ratios or list(RATIOS_CONFIG.keys())
    auto_tuning = req.auto_tuning
    
    # Run in separate thread to prevent blocking
    thread = threading.Thread(
        target=pipeline.run_multi_horizon_forecast,
        kwargs={
            "job_id": job_id,
            "selected_models": models,
            "selected_metrics": metrics,
            "selected_horizons": horizons,
            "selected_ratios": ratios,
            "auto_tuning": auto_tuning
        }
    )
    thread.daemon = True
    thread.start()
    
    return {
        "status": "started",
        "job_id": job_id,
        "total_experiments": len(models) * len(horizons) * len(ratios) * len(metrics)
    }

@app.get("/api/forecast/status/{job_id}")
async def get_forecast_status(job_id: str):
    """Polls status and live progress of a job."""
    if job_id not in pipeline.active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return pipeline.active_jobs[job_id]

@app.get("/api/forecast/stream/{job_id}")
async def stream_forecast_progress(job_id: str):
    """Server-Sent Events (SSE) stream for live progress updates."""
    async def event_generator():
        while True:
            if job_id not in pipeline.active_jobs:
                yield f"data: {json.dumps({'status': 'NOT_FOUND'})}\n\n"
                break
                
            job_data = pipeline.active_jobs[job_id]
            # Emit status without full bulky results
            light_data = {
                "job_id": job_id,
                "status": job_data["status"],
                "progress": job_data["progress"],
                "completed": job_data["completed"],
                "total": job_data["total"],
                "current_model": job_data.get("current_model", ""),
                "current_horizon": job_data.get("current_horizon", ""),
                "current_ratio": job_data.get("current_ratio", ""),
                "current_metric": job_data.get("current_metric", ""),
                "error": job_data.get("error", None)
            }
            yield f"data: {json.dumps(light_data)}\n\n"
            
            if job_data["status"] in ["COMPLETED", "ERROR", "CANCELLED"]:
                break
                
            await asyncio.sleep(0.3)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/forecast/results/{job_id}")
async def get_forecast_results(job_id: str):
    """Retrieves full formatted results and cards for a completed job."""
    if job_id not in pipeline.active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = pipeline.active_jobs[job_id]
    return {
        "status": job["status"],
        "total": job["total"],
        "completed": job["completed"],
        "elapsed_seconds": job.get("elapsed_seconds", 0),
        "results": job.get("results", [])
    }

@app.post("/api/forecast/cancel/{job_id}")
async def cancel_forecast(job_id: str):
    """Cancels a running job."""
    pipeline.cancel_job(job_id)
    return {"status": "cancelled", "job_id": job_id}

@app.post("/api/forecast/upload-actual")
async def upload_actual_data(file: UploadFile = File(...)):
    """
    Parses uploaded actual market data (CSV or Excel) for post-forecast comparison and chart overlay.
    Strictly post-forecast: NEVER used for training, prediction, or tuning.
    """
    import io
    import pandas as pd
    try:
        content = await file.read()
        filename = file.filename or "uploaded.csv"
        is_excel = filename.lower().endswith((".xlsx", ".xls"))
        
        if is_excel:
            df_raw = pd.read_excel(io.BytesIO(content), header=None)
        else:
            try:
                df_raw = pd.read_csv(io.BytesIO(content), header=None)
            except Exception:
                df_raw = pd.read_csv(io.BytesIO(content), sep=None, engine="python", header=None)

        if df_raw.empty:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Check if first row is a header
        first_row_str = " ".join([str(x).lower() for x in df_raw.iloc[0].values])
        has_header = any(k in first_row_str for k in ["date", "close", "copper", "price", "time"])

        if has_header:
            if is_excel:
                df = pd.read_excel(io.BytesIO(content))
            else:
                try:
                    df = pd.read_csv(io.BytesIO(content))
                except Exception:
                    df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
                    
            date_col = next((c for c in df.columns if "date" in str(c).lower() or "time" in str(c).lower()), df.columns[0])
            close_col = next((c for c in df.columns if str(c).strip().lower() in ["copper_close", "close", "copper close", "copper_close_price"]), None)
            if close_col is None:
                close_col = next((c for c in df.columns if "close" in str(c).lower() and not any(x in str(c).lower() for x in ["open", "high", "low", "prev"])), None)
            if close_col is None:
                close_col = df.columns[4] if len(df.columns) >= 5 else df.columns[1]
                
            df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
            df["_parsed_close"] = pd.to_numeric(df[close_col], errors="coerce")
        else:
            df = df_raw.copy()
            df["_parsed_date"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
            close_idx = 4 if df.shape[1] >= 5 else (1 if df.shape[1] >= 2 else 0)
            df["_parsed_close"] = pd.to_numeric(df.iloc[:, close_idx], errors="coerce")

        valid = df.dropna(subset=["_parsed_date", "_parsed_close"]).sort_values("_parsed_date")
        if valid.empty:
            raise HTTPException(status_code=400, detail="Could not extract valid Date and Close price records from file.")

        records = [
            {
                "date": r["_parsed_date"].strftime("%Y-%m-%d"),
                "actual_close": round(float(r["_parsed_close"]), 4)
            }
            for _, r in valid.iterrows()
        ]

        return {
            "status": "success",
            "filename": filename,
            "total_records": len(records),
            "date_min": records[0]["date"],
            "date_max": records[-1]["date"],
            "records": records
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse actual data file: {str(e)}")

@app.post("/api/data/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Allows uploading custom market CSV."""
    global data_mgr, pipeline
    try:
        content = await file.read()
        with open("custom_market_data.csv", "wb") as f:
            f.write(content)
            
        data_mgr = DataManager("custom_market_data.csv")
        pipeline = ForecastingPipeline(data_mgr)
        return {"status": "success", "message": f"Uploaded and processed {len(data_mgr.raw_df)} rows"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")

# Mount static web directory
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
