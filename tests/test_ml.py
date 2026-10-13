import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml.models import ModelManager
import pandas as pd
import numpy as np

def test_ml_pipeline():
    manager = ModelManager(models_dir="tests/test_models")
    
    # Dummy data
    X_train = pd.DataFrame({
        'co2_1h_avg': [400, 410, 420, 430, 440],
        'Temperature': [20, 21, 22, 23, 24],
        'Humidity': [50, 51, 52, 53, 54],
        'PM2S': [10, 11, 12, 13, 14],
        'AQI': [30, 31, 32, 33, 34],
        'hour_sin': [0, 1, 0, -1, 0],
        'hour_cos': [1, 0, -1, 0, 1],
        'month_sin': [0]*5,
        'month_cos': [1]*5
    })
    y_train = pd.Series([410, 420, 430, 440, 450])
    y_train_labels = pd.Series([1, 1, 1, 1, 2])
    
    # Train
    manager.train_linear_regression(X_train, y_train)
    manager.train_random_forest(X_train, y_train)
    manager.train_decision_tree(X_train, y_train_labels)
    
    # Load
    manager.load_models()
    assert manager.lr_model is not None
    assert manager.rf_model is not None
    assert manager.dt_model is not None
    
    # Predict
    mean_pred, conf_low, conf_high = manager.predict_rf_with_confidence(X_train.iloc[[-1]])
    assert len(mean_pred) == 1
    assert conf_low[0] <= mean_pred[0] <= conf_high[0]
    
    # Classify
    assert manager.classify_zone(390) == 0
    assert manager.classify_zone(460) == 2
