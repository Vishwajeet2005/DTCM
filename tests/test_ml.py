"""
Tests for ML models and prediction utilities in DTCM.
"""
import os
import tempfile
import pandas as pd
import numpy as np
import pytest
import joblib

# Assuming the functions are available in dtcm.ml or dtcm.models
# We mock or use realistic function names if they don't exist yet, 
# but the prompt implies we are building tests for the project.
from ml import (
    train_linear_regression,
    train_random_forest,
    get_confidence_intervals,
    train_decision_tree_classifier,
    save_model,
    load_model,
    predict_short_term,
    classify_zones
)

def _generate_synthetic_regression_data(n_samples=100):
    """Generate synthetic DataFrame for testing regression models."""
    np.random.seed(42)
    X = pd.DataFrame({
        'temperature': np.random.normal(22, 2, n_samples),
        'humidity': np.random.normal(50, 5, n_samples),
        'occupancy': np.random.randint(0, 10, n_samples)
    })
    y = 400 + 5 * X['occupancy'] + 2 * X['temperature'] + np.random.normal(0, 10, n_samples)
    return X, y

def _generate_synthetic_classification_data(n_samples=100):
    """Generate synthetic DataFrame for testing classification models."""
    np.random.seed(42)
    X = pd.DataFrame({
        'co2_level': np.random.normal(400, 50, n_samples),
        'temperature': np.random.normal(22, 2, n_samples)
    })
    # Target classes: 0 (Normal), 1 (Warning), 2 (Critical)
    y = np.where(X['co2_level'] > 450, 1, 0)
    y = np.where(X['co2_level'] > 500, 2, y)
    return X, y

def test_linear_regression_train_predict():
    """Test training and predicting with Linear Regression."""
    X, y = _generate_synthetic_regression_data()
    model = train_linear_regression(X, y)
    assert model is not None
    
    predictions = model.predict(X)
    assert len(predictions) == len(X)
    assert isinstance(predictions, np.ndarray)

def test_random_forest_train_predict():
    """Test training and predicting with Random Forest."""
    X, y = _generate_synthetic_regression_data()
    model = train_random_forest(X, y)
    assert model is not None
    
    predictions = model.predict(X)
    assert len(predictions) == len(X)

def test_confidence_intervals():
    """Test confidence intervals calculation."""
    predictions = np.array([400.0, 410.0, 420.0])
    std_dev = 15.0
    lower, upper = get_confidence_intervals(predictions, std_dev)
    
    assert len(lower) == len(predictions)
    assert len(upper) == len(predictions)
    assert (lower < predictions).all()
    assert (upper > predictions).all()

def test_decision_tree_classification():
    """Test Decision Tree for classification."""
    X, y = _generate_synthetic_classification_data()
    model = train_decision_tree_classifier(X, y)
    assert model is not None
    
    predictions = model.predict(X)
    assert len(predictions) == len(X)
    assert set(predictions).issubset({0, 1, 2})

def test_model_save_load():
    """Test saving and loading ML models."""
    X, y = _generate_synthetic_regression_data()
    model = train_linear_regression(X, y)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, 'test_model.pkl')
        save_model(model, model_path)
        assert os.path.exists(model_path)
        
        loaded_model = load_model(model_path)
        assert loaded_model is not None
        
        # Test predictions match
        np.testing.assert_array_equal(
            model.predict(X),
            loaded_model.predict(X)
        )

def test_predict_short_term_output_format():
    """Test the output format of short-term prediction utility."""
    X, _ = _generate_synthetic_regression_data(10)
    result = predict_short_term(X)
    
    assert isinstance(result, list)
    assert len(result) == len(X)
    if len(result) > 0:
        assert 'timestamp' in result[0]
        assert 'predicted_co2' in result[0]
        assert 'lower_bound' in result[0]
        assert 'upper_bound' in result[0]

def test_classify_zones_output():
    """Test the output format of zone classification."""
    zones_data = pd.DataFrame({
        'zone_id': ['Z1', 'Z2'],
        'co2_level': [420, 510],
        'temperature': [22, 24]
    })
    
    result = classify_zones(zones_data)
    assert isinstance(result, dict)
    assert 'Z1' in result
    assert 'Z2' in result
    assert result['Z1'] in ['Normal', 'Warning', 'Critical']
    assert result['Z2'] == 'Critical' # based on 510 > 500 threshold

