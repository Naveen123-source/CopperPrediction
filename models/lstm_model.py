"""
Leakage-Free LSTM Multi-Horizon Direct Forecasting Model
Constructs chronological sliding sequences (window length W) with MinMaxScaler fitted strictly on X_train.
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from .base import BaseModel

class LSTMForecastModel(BaseModel):
    def __init__(self, horizon=1, params=None):
        default_params = {
            "window_size": 10,
            "lstm_units": 32,
            "dropout": 0.1,
            "epochs": 20,
            "batch_size": 32,
            "learning_rate": 0.005
        }
        if params:
            default_params.update(params)
        super().__init__(name="LSTM", horizon=horizon, params=default_params)
        self.scaler_X = None
        self.scaler_y = None
        self.tf_model = None
        self.window_size = self.params.get("window_size", 10)
        self.last_train_seq = None
        
    def _create_sequences(self, X_arr, y_arr=None):
        """Creates chronological non-shuffled sliding sequences [samples, window_size, features]."""
        w = self.window_size
        n = len(X_arr)
        if n < w:
            # Pad if shorter than window
            pad_len = w - n
            pad = np.tile(X_arr[0:1], (pad_len, 1))
            X_padded = np.vstack([pad, X_arr])
            seqs = [X_padded]
            return np.array(seqs), y_arr
            
        seqs = []
        targets = []
        for i in range(w, n + 1):
            seqs.append(X_arr[i - w:i])
            if y_arr is not None:
                targets.append(y_arr[i - 1])
                
        if y_arr is not None:
            return np.array(seqs), np.array(targets)
        return np.array(seqs)
        
    def fit(self, X_train, y_train, **kwargs):
        # 1. Scale strictly on training data
        self.scaler_X = MinMaxScaler()
        X_train_scaled = self.scaler_X.fit_transform(X_train)
        
        self.scaler_y = MinMaxScaler()
        y_train_mat = np.asarray(y_train).reshape(-1, 1)
        y_train_scaled = self.scaler_y.fit_transform(y_train_mat).flatten()
        
        # 2. Build non-shuffled chronological sequences
        X_seq, y_seq = self._create_sequences(X_train_scaled, y_train_scaled)
        self.last_train_seq = X_train_scaled[-self.window_size:]
        
        # 3. Try TensorFlow LSTM Network first; fall back to Sequence MLP if unavailable
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
            from tensorflow.keras.optimizers import Adam
            
            tf.random.set_seed(42)
            model = Sequential([
                Input(shape=(self.window_size, X_train.shape[1])),
                LSTM(self.params.get("lstm_units", 32), return_sequences=False),
                Dropout(self.params.get("dropout", 0.1)),
                Dense(16, activation="relu"),
                Dense(1)
            ])
            
            optimizer = Adam(learning_rate=self.params.get("learning_rate", 0.005))
            model.compile(optimizer=optimizer, loss="mse")
            
            model.fit(
                X_seq, y_seq,
                epochs=self.params.get("epochs", 20),
                batch_size=self.params.get("batch_size", 32),
                verbose=0,
                shuffle=False  # Strict chronological ordering
            )
            self.tf_model = model
            self.model_type = "tf"
        except (ImportError, ModuleNotFoundError):
            # Resilient sequence MLP fallback preserving identical sliding window & zero leakage
            import warnings
            from sklearn.exceptions import ConvergenceWarning
            from sklearn.neural_network import MLPRegressor
            flat_X_seq = X_seq.reshape(len(X_seq), -1)
            model = MLPRegressor(
                hidden_layer_sizes=(self.params.get("lstm_units", 32), 16),
                max_iter=self.params.get("epochs", 40),
                learning_rate_init=self.params.get("learning_rate", 0.005),
                random_state=42,
                shuffle=False
            )
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ConvergenceWarning)
                model.fit(flat_X_seq, y_seq)
            self.tf_model = model
            self.model_type = "mlp_seq"
        
        self.is_fitted = True
        self.best_params = self.params.copy()
        return self
        
    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("LSTM model not fitted.")
            
        X_scaled = self.scaler_X.transform(X)
        n = len(X_scaled)
        w = self.window_size
        
        # Prepend last training sequence to ensure valid sequence length for the first w-1 points
        if self.last_train_seq is not None:
            full_seq = np.vstack([self.last_train_seq, X_scaled])
        else:
            full_seq = X_scaled
            
        seqs = []
        for i in range(w, len(full_seq)):
            seqs.append(full_seq[i - w:i])
            
        if len(seqs) == 0:
            seqs = [full_seq[-w:]]
            
        seqs_mat = np.array(seqs)
        if getattr(self, "model_type", "tf") == "tf":
            pred_scaled = self.tf_model.predict(seqs_mat, verbose=0)
        else:
            flat_seqs = seqs_mat.reshape(len(seqs_mat), -1)
            pred_scaled = self.tf_model.predict(flat_seqs).reshape(-1, 1)
        
        # Inverse transform target back to actual price scale
        pred_unscaled = self.scaler_y.inverse_transform(pred_scaled).flatten()
        
        # Match output length with input X length
        if len(pred_unscaled) > n:
            pred_unscaled = pred_unscaled[-n:]
        elif len(pred_unscaled) < n:
            pred_unscaled = np.pad(pred_unscaled, (n - len(pred_unscaled), 0), mode="edge")
            
        return pred_unscaled
