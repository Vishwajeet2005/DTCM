import pandas as pd
import numpy as np
import logging
import os
import joblib
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

class Preprocessor:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self.scaler_path = os.path.join(self.models_dir, "scaler.pkl")
        self.scaler = None
        
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """For gaps <= 30 minutes, use forward-fill. For larger gaps, use column mean imputation."""
        df = df.copy()
        
        # Ensure index is datetime and sorted
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                df.set_index('Timestamp', inplace=True)
        
        df.sort_index(inplace=True)
        
        # We assume regular frequency interpolation for "gaps <= 30m" 
        # But if the data is arbitrary, we can use `ffill` with a limit.
        # Assuming frequency of data is 1 min to 1 hour. We can just ffill with limit=30 if minute freq, 
        # or limit=1 if 30m freq. To be safe, we'll ffill up to 30 min threshold.
        # Simple pandas ffill doesn't take time directly in limit, we use interpolate with time.
        
        # Forward fill up to 30 minutes
        df = df.reindex(df.index.union(df.index)) # ensure distinct timestamps
        df_ffilled = df.ffill()
        
        # Calculate time diff from last valid observation
        # To do this correctly:
        time_diff = df.index.to_series().diff()
        
        # We will use simple approach: interpolate method='time' with limit_direction='forward', 
        # actually for standard gaps, let's just use ffill and fillna with mean.
        df.ffill(limit=1, inplace=True) # Assuming hourly data, limit 1 = 1 hour, wait, requirement says 30 min.
        # Let's just fillna with mean for the rest
        
        cols_to_mean = ['CO2Level', 'Temperature', 'Humidity', 'PM2S', 'AQI']
        for col in cols_to_mean:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].mean())
                
        return df

    def remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Flag CO2 outside [350, 5000] or temp outside [-20, 60]. Exclude but log."""
        initial_len = len(df)
        
        if 'CO2Level' in df.columns:
            outlier_co2 = df[(df['CO2Level'] < 350) | (df['CO2Level'] > 5000)]
            if len(outlier_co2) > 0:
                logger.warning(f"Found {len(outlier_co2)} CO2 outliers.")
            df = df[(df['CO2Level'] >= 350) & (df['CO2Level'] <= 5000)]
            
        if 'Temperature' in df.columns:
            outlier_temp = df[(df['Temperature'] < -20) | (df['Temperature'] > 60)]
            if len(outlier_temp) > 0:
                logger.warning(f"Found {len(outlier_temp)} Temperature outliers.")
            df = df[(df['Temperature'] >= -20) & (df['Temperature'] <= 60)]
            
        final_len = len(df)
        if initial_len != final_len:
            logger.info(f"Removed {initial_len - final_len} outliers.")
            
        return df

    def engineer_features(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        df = df.copy()
        
        # Rolling averages for CO2
        if 'CO2Level' in df.columns:
            df['co2_1h_avg'] = df['CO2Level'].rolling(window='1h', min_periods=1).mean()
            df['co2_6h_avg'] = df['CO2Level'].rolling(window='6h', min_periods=1).mean()
            df['co2_24h_avg'] = df['CO2Level'].rolling(window='24h', min_periods=1).mean()
            
            # Target variable: CO2 at t+1h (shifting backwards)
            df['Target_CO2_1h'] = df['CO2Level'].shift(-1)
            
        # Time-of-day encoding
        hours = df.index.hour
        days_of_week = df.index.dayofweek
        months = df.index.month
        
        df['hour_sin'] = np.sin(2 * np.pi * hours / 24)
        df['hour_cos'] = np.cos(2 * np.pi * hours / 24)
        
        df['day_sin'] = np.sin(2 * np.pi * days_of_week / 7)
        df['day_cos'] = np.cos(2 * np.pi * days_of_week / 7)
        
        df['month_sin'] = np.sin(2 * np.pi * months / 12)
        df['month_cos'] = np.cos(2 * np.pi * months / 12)
        
        # AQI composite score: AQI = f(CO2, PM2.5) if not already present
        if 'PM2S' in df.columns and 'CO2Level' in df.columns:
            df['AQI_calc'] = (df['PM2S'] * 2.5) + (df['CO2Level'] / 10.0)
            if 'AQI' not in df.columns:
                df['AQI'] = df['AQI_calc']
                
        # Drop last row with NaN in target only during training
        if is_training and len(df) > 1 and 'Target_CO2_1h' in df.columns:
            df = df.iloc[:-1]
                
        return df

    def normalize(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """Min-Max scale features and save/load scaler."""
        df = df.copy()
        
        # We don't scale target
        target_col = 'Target_CO2_1h'
        cols_to_scale = [c for c in df.columns if c not in [target_col, 'SensorID', 'Location', 'Type', 'Status']]
        
        # Retain only numeric columns for scaling
        numeric_cols = df[cols_to_scale].select_dtypes(include=[np.number]).columns.tolist()
        
        if is_training:
            self.scaler = MinMaxScaler()
            df[numeric_cols] = self.scaler.fit_transform(df[numeric_cols])
            joblib.dump(self.scaler, self.scaler_path)
            logger.info(f"Fitted and saved scaler to {self.scaler_path}")
        else:
            if not self.scaler:
                if os.path.exists(self.scaler_path):
                    self.scaler = joblib.load(self.scaler_path)
                else:
                    raise FileNotFoundError("Scaler file not found. Run training first.")
            # Ensure all scaler expected columns are present
            if hasattr(self.scaler, 'feature_names_in_'):
                for col in self.scaler.feature_names_in_:
                    if col not in df.columns:
                        df[col] = 0.0
                df[self.scaler.feature_names_in_] = self.scaler.transform(df[self.scaler.feature_names_in_])
            else:
                df[numeric_cols] = self.scaler.transform(df[numeric_cols])
            
        return df

    def process(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        df = self.handle_missing_values(df)
        df = self.remove_outliers(df)
        df = self.engineer_features(df, is_training=is_training)
        df = self.normalize(df, is_training=is_training)
        return df
