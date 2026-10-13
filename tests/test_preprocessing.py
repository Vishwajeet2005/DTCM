import pytest
import pandas as pd
import numpy as np
import datetime
from processing.preprocessor import Preprocessor

@pytest.fixture
def sample_data():
    dates = pd.date_range("2023-01-01 00:00:00", periods=5, freq="1h")
    df = pd.DataFrame({
        "Timestamp": dates,
        "SensorID": [1, 1, 1, 1, 1],
        "CO2Level": [400, 410, np.nan, 300, 500], # One NaN, one outlier
        "Temperature": [20, 21, 22, -30, 25],     # One outlier
        "Humidity": [50, 55, np.nan, 60, 65],
        "PM2S": [10, 12, 11, 15, 14],
        "AQI": [30, 35, 33, 40, 38]
    })
    return df

def test_handle_missing_values(sample_data):
    prep = Preprocessor()
    df_clean = prep.handle_missing_values(sample_data)
    assert df_clean["CO2Level"].isna().sum() == 0
    assert df_clean["Humidity"].isna().sum() == 0
    # The mean of remaining CO2 is (400+410+300+500)/4 = 402.5. 
    # But because of ffill (limit=1), index 2 will get 410.

def test_remove_outliers(sample_data):
    prep = Preprocessor()
    sample_data.set_index("Timestamp", inplace=True)
    df_clean = prep.remove_outliers(sample_data)
    # CO2=300 is removed, Temp=-30 is removed
    assert len(df_clean) == 3
    assert (df_clean["CO2Level"] >= 350).all()
    assert (df_clean["Temperature"] >= -20).all()

def test_engineer_features(sample_data):
    prep = Preprocessor()
    sample_data.set_index("Timestamp", inplace=True)
    df_clean = prep.engineer_features(sample_data)
    assert "co2_1h_avg" in df_clean.columns
    assert "hour_sin" in df_clean.columns
    # Last row dropped because Target_CO2_1h is NaN
    assert len(df_clean) == 4
    assert "Target_CO2_1h" in df_clean.columns

def test_full_pipeline(sample_data):
    prep = Preprocessor()
    df_processed = prep.process(sample_data, is_training=True)
    assert "Target_CO2_1h" in df_processed.columns
    assert len(df_processed) > 0
    # Values should be scaled between 0 and 1
    assert df_processed["Temperature"].max() <= 1.0
    assert df_processed["Temperature"].min() >= 0.0
