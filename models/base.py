"""
Abstract Base Model Class for Multi-Horizon Direct Forecasting
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

class BaseModel(ABC):
    def __init__(self, name="BaseModel", horizon=1, params=None):
        self.name = name
        self.horizon = horizon
        self.params = params or {}
        self.model = None
        self.is_fitted = False
        self.best_params = {}
        
    @abstractmethod
    def fit(self, X_train, y_train, **kwargs):
        """Fit model strictly on training data."""
        pass
        
    @abstractmethod
    def predict(self, X):
        """Generate predictions for given feature matrix."""
        pass
        
    def get_params(self):
        return self.params
        
    def set_params(self, **params):
        self.params.update(params)
        return self
