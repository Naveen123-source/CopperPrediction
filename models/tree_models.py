"""
Tree-Based Models: XGBoost, CatBoost, LightGBM, RandomForest
"""

import numpy as np
import pandas as pd
from .base import BaseModel

# 1. XGBoost Model
class XGBoostModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": -1
        }
        if params:
            default_params.update(params)
        super().__init__(name="XGBoost", horizon=horizon, params=default_params)
        
    def fit(self, X_train, y_train, **kwargs):
        import xgboost as xgb
        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        return self.model.predict(X)

# 2. CatBoost Model
class CatBoostModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "iterations": 150,
            "depth": 5,
            "learning_rate": 0.05,
            "l2_leaf_reg": 3.0,
            "random_seed": 42,
            "verbose": 0
        }
        if params:
            default_params.update(params)
        super().__init__(name="CatBoost", horizon=horizon, params=default_params)
        
    def fit(self, X_train, y_train, **kwargs):
        from catboost import CatBoostRegressor
        self.model = CatBoostRegressor(**self.params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        return self.model.predict(X)

# 3. LightGBM Model
class LightGBMModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "n_estimators": 100,
            "max_depth": 5,
            "num_leaves": 31,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "verbose": -1,
            "n_jobs": -1
        }
        if params:
            default_params.update(params)
        super().__init__(name="LightGBM", horizon=horizon, params=default_params)
        
    def fit(self, X_train, y_train, **kwargs):
        import lightgbm as lgb
        self.model = lgb.LGBMRegressor(**self.params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        return self.model.predict(X)

# 4. RandomForest Model
class RandomForestModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "n_estimators": 100,
            "max_depth": 8,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "random_state": 42,
            "n_jobs": -1
        }
        if params:
            default_params.update(params)
        super().__init__(name="RandomForest", horizon=horizon, params=default_params)
        
    def fit(self, X_train, y_train, **kwargs):
        from sklearn.ensemble import RandomForestRegressor
        self.model = RandomForestRegressor(**self.params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        return self.model.predict(X)
