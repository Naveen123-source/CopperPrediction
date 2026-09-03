"""
Leakage-Free Stacking Ensemble Model
Constructs out-of-fold meta-features using strictly chronological TimeSeriesSplit folds on training data.
Meta-model: Regularized Ridge / ElasticNet Meta-Regressor.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostRegressor
from .base import BaseModel

class StackingEnsembleModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "n_splits": 4,
            "meta_alpha": 1.0,
            "random_state": 42
        }
        if params:
            default_params.update(params)
        super().__init__(name="Stacking Ensemble", horizon=horizon, params=default_params)
        self.base_models = {}
        self.meta_model = None
        
    def _create_base_instances(self):
        return {
            "xgb": xgb.XGBRegressor(n_estimators=80, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=-1),
            "cat": CatBoostRegressor(iterations=100, depth=4, learning_rate=0.05, verbose=0, random_seed=42),
            "lgb": lgb.LGBMRegressor(n_estimators=80, max_depth=4, learning_rate=0.05, verbose=-1, random_state=42, n_jobs=-1),
            "rf": RandomForestRegressor(n_estimators=60, max_depth=6, random_state=42, n_jobs=-1)
        }
        
    def fit(self, X_train, y_train, **kwargs):
        X_mat = np.asarray(X_train)
        y_mat = np.asarray(y_train)
        n = len(X_mat)
        
        n_splits = min(self.params["n_splits"], max(2, n // 100))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        # Base model names
        model_keys = ["xgb", "cat", "lgb", "rf"]
        num_models = len(model_keys)
        
        # Out-of-fold predictions storage for training meta-model
        # Start storing OOF predictions from the first validation split
        oof_meta_features = []
        oof_targets = []
        
        purge_gap = max(0, self.horizon)
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_mat)):
            # Purge fold training boundary by horizon to eliminate target overlap into OOF validation fold
            if len(train_idx) > purge_gap + 20:
                purged_train_idx = train_idx[:-purge_gap]
            else:
                purged_train_idx = train_idx[:max(1, len(train_idx) // 2)]

            fold_X_tr, fold_y_tr = X_mat[purged_train_idx], y_mat[purged_train_idx]
            fold_X_val, fold_y_val = X_mat[val_idx], y_mat[val_idx]
            
            fold_preds = []
            for k in model_keys:
                base_inst = self._create_base_instances()[k]
                base_inst.fit(fold_X_tr, fold_y_tr)
                pred_val = base_inst.predict(fold_X_val)
                fold_preds.append(pred_val)
                
            fold_meta = np.column_stack(fold_preds)
            oof_meta_features.append(fold_meta)
            oof_targets.append(fold_y_val)
            
        OOF_X = np.vstack(oof_meta_features)
        OOF_y = np.concatenate(oof_targets)
        
        # Fit Meta-model on TimeSeries OOF predictions
        self.meta_model = Ridge(alpha=self.params["meta_alpha"], positive=True)
        self.meta_model.fit(OOF_X, OOF_y)
        
        # Finally, train all base models on the FULL training dataset
        self.base_models = self._create_base_instances()
        for k, inst in self.base_models.items():
            inst.fit(X_train, y_train)
            
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Stacking Ensemble not fitted.")
            
        # Generate base predictions
        base_preds = []
        for k in ["xgb", "cat", "lgb", "rf"]:
            pred = self.base_models[k].predict(X)
            base_preds.append(pred)
            
        meta_X = np.column_stack(base_preds)
        return self.meta_model.predict(meta_X)
