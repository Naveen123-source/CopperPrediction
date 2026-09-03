"""
Models package for Multi-Horizon Copper Price Forecasting
"""

from .base import BaseModel
from .tree_models import XGBoostModel, CatBoostModel, LightGBMModel, RandomForestModel
from .stage_regression import StageRegressionModel
from .stacking import StackingEnsembleModel
from .time_series_models import ARIMAForecastModel, SARIMAXForecastModel
from .lstm_model import LSTMForecastModel

MODEL_REGISTRY = {
    "XGBoost": XGBoostModel,
    "CatBoost": CatBoostModel,
    "LightGBM": LightGBMModel,
    "RandomForest": RandomForestModel,
    "Stacking Ensemble": StackingEnsembleModel,
    "Stage Regression": StageRegressionModel,
    "ARIMA": ARIMAForecastModel,
    "SARIMAX": SARIMAXForecastModel,
    "LSTM": LSTMForecastModel
}
