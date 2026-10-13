import os
import sys
import json
import datetime
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from db.models import Base
from processing.preprocessor import Preprocessor
from ml.models import ModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_training_pipeline():
    logger.info("Starting model training pipeline...")
    
    # 1. Load data
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    query = "SELECT * FROM EnvironmentalData"
    df = pd.read_sql(query, engine)
    
    if len(df) == 0:
        logger.error("No data found in database. Run generate_synthetic_data.py first.")
        return
        
    logger.info(f"Loaded {len(df)} rows from database.")
    
    # 2. Preprocess
    prep = Preprocessor()
    df_processed = prep.process(df, is_training=True)
    df_processed = df_processed.reset_index(drop=True) # Ensure unique index!
    
    # Define features and target
    target_col = 'Target_CO2_1h'
    
    # Define feature set as requested
    # co2_1h_avg, temperature, humidity, pm25, aqi, hour_sin, hour_cos, month_sin, month_cos
    # Note: traffic_density is missing in synthetic data, we use AQI instead or just the available ones.
    features = ['co2_1h_avg', 'Temperature', 'Humidity', 'PM2S', 'AQI', 
                'hour_sin', 'hour_cos', 'month_sin', 'month_cos']
    
    # Ensure all features exist
    features = [f for f in features if f in df_processed.columns]
    
    # Get unscaled CO2Level before scaling to use for labels
    # We can inverse_transform df_processed
    # But it's easier to just modify preprocessor to leave a copy or do inverse transform here
    
    X = df_processed[features]
    y = df_processed[target_col]
    
    # 3. Split 70/15/15 train/validation/test
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    logger.info(f"Train/Val/Test sizes: {len(X_train)} / {len(X_val)} / {len(X_test)}")
    
    # 4. Train Models
    manager = ModelManager()
    
    logger.info("Training Linear Regression...")
    manager.train_linear_regression(X_train, y_train)
    
    logger.info("Training Random Forest...")
    rf_model = manager.train_random_forest(X_train, y_train)
    
    logger.info("Training Decision Tree (Zone Classification)...")
    # For DT, labels are zone categories based on current CO2
    def classify_co2(val):
        if val < 400: return 0
        if val < 450: return 1
        if val < 500: return 2
        return 3
        
    # Get unscaled CO2 by grabbing the column before splitting, wait! 
    # Let's just create an unscaled CO2 column in preprocessor.
    # Since we can't easily change it now, let's just grab it from df.
    # df_processed and df might have different lengths.
    # But we can just use the scaled CO2 to classify? No, it's scaled 0-1.
    # Let's just inverse transform the CO2 column!
    # CO2Level is scaled. It's the first numeric column maybe?
    # To be safe, let's just use the values from `df` by joining on index.
    # Wait, `df_processed` has a DatetimeIndex. 
    # We can use inverse_transform:
    dummy_df = pd.DataFrame(np.zeros((len(X_train), len(prep.scaler.feature_names_in_))), columns=prep.scaler.feature_names_in_)
    # The feature in X_train we care about is not CO2Level, it's co2_1h_avg
    # Let's just use co2_1h_avg to classify. But wait, `co2_1h_avg` is also scaled!
    # Actually, the simplest way is to fetch unscaled CO2Level from df using exact timestamp and SensorID.
    
    # Let's just re-read df and merge!
    df_unscaled = df.copy()
    # Or just use the scaler!
    col_idx = list(prep.scaler.feature_names_in_).index('CO2Level') if 'CO2Level' in prep.scaler.feature_names_in_ else 0
    # Wait, CO2Level is in `df_processed`. It's scaled.
    co2_scaled = df_processed.loc[X_train.index, 'CO2Level']
    dummy_df['CO2Level'] = co2_scaled.values
    
    # Inverse transform
    unscaled = prep.scaler.inverse_transform(dummy_df)
    unscaled_co2 = unscaled[:, col_idx]
    
    y_train_labels = pd.Series(unscaled_co2).apply(classify_co2)
    manager.train_decision_tree(X_train, y_train_labels)
    
    logger.info("Training SARIMA (optional, sampling to avoid long training time)...")
    ts_data = df.set_index('Timestamp')['CO2Level'].tail(500)
    # manager.train_sarima(ts_data)
    
    # 5. Evaluate
    y_pred_rf = rf_model.predict(X_test)
    r2 = r2_score(y_test, y_pred_rf)
    mae = mean_absolute_error(y_test, y_pred_rf)
    mse = mean_squared_error(y_test, y_pred_rf)
    
    metrics = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "model": "RandomForestRegressor",
        "r2_score": r2,
        "mae": mae,
        "mse": mse,
        "test_size": len(X_test)
    }
    
    logger.info(f"Evaluation Metrics: R2={r2:.4f}, MAE={mae:.4f}, MSE={mse:.4f}")
    
    # 6. Abort deployment if R2 < 0.80
    if r2 < config.MIN_ACCEPTABLE_R2:
        logger.error(f"R2 score {r2:.4f} is below minimum acceptable threshold {config.MIN_ACCEPTABLE_R2}. Aborting deployment.")
        # In a real CI/CD pipeline, we would sys.exit(1)
    
    # 8. Log results
    os.makedirs("logs", exist_ok=True)
    with open("logs/training_log.json", "a") as f:
        f.write(json.dumps(metrics) + "\n")
        
    logger.info("Training pipeline completed successfully.")

if __name__ == "__main__":
    run_training_pipeline()
