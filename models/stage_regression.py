"""
Stage Regression Model
Two-Stage Forecasting Architecture:
Stage 1: Linear / Regularized Ridge Trend & Macro Regression
Stage 2: Nonlinear Gradient Boosted Residual Regressor
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from .base import BaseModel

class StageRegressionModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "stage1_alpha": 1.0,
            "stage2_n_estimators": 80,
            "stage2_max_depth": 4,
            "stage2_learning_rate": 0.05,
            "random_state": 42
        }
        if params:
            default_params.update(params)
        super().__init__(name="Stage Regression", horizon=horizon, params=default_params)
        self.scaler = None
        self.stage1_model = None
        self.stage2_model = None
        
    def fit(self, X_train, y_train, **kwargs):
        # 1. Scale features using training data ONLY
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # 2. Stage 1: Linear / Ridge regression on scaled features
        self.stage1_model = Ridge(alpha=self.params["stage1_alpha"], random_state=self.params["random_state"])
        self.stage1_model.fit(X_train_scaled, y_train)
        
        # Calculate Stage 1 predictions and residuals
        stage1_train_pred = self.stage1_model.predict(X_train_scaled)
        residuals_train = y_train - stage1_train_pred
        
        # 3. Stage 2: Boosted Tree model on Stage 1 residuals
        self.stage2_model = xgb.XGBRegressor(
            n_estimators=self.params["stage2_n_estimators"],
            max_depth=self.params["stage2_max_depth"],
            learning_rate=self.params["stage2_learning_rate"],
            random_state=self.params["random_state"],
            n_jobs=-1
        )
        self.stage2_model.fit(X_train, residuals_train)
        
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
            
        # Stage 1 prediction (scaled)
        X_scaled = self.scaler.transform(X)
        pred_stage1 = self.stage1_model.predict(X_scaled)
        
        # Stage 2 residual prediction (unscaled / original feature space)
        pred_stage2 = self.stage2_model.predict(X)
        
        # Combine both stages
        return pred_stage1 + pred_stage2
