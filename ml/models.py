import os
import joblib
import numpy as np
import logging
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier
from statsmodels.tsa.statespace.sarimax import SARIMAX

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self.lr_path = os.path.join(self.models_dir, "linear_regression.pkl")
        self.rf_path = os.path.join(self.models_dir, "random_forest.pkl")
        self.dt_path = os.path.join(self.models_dir, "decision_tree.pkl")
        self.sarima_path = os.path.join(self.models_dir, "sarima.pkl")
        
        self.lr_model = None
        self.rf_model = None
        self.dt_model = None
        self.sarima_model = None
        
    def load_models(self):
        if os.path.exists(self.lr_path):
            self.lr_model = joblib.load(self.lr_path)
        if os.path.exists(self.rf_path):
            self.rf_model = joblib.load(self.rf_path)
        if os.path.exists(self.dt_path):
            self.dt_model = joblib.load(self.dt_path)
        if os.path.exists(self.sarima_path):
            self.sarima_model = joblib.load(self.sarima_path)

    def train_linear_regression(self, X_train, y_train):
        self.lr_model = LinearRegression()
        self.lr_model.fit(X_train, y_train)
        joblib.dump(self.lr_model, self.lr_path)
        logger.info("Trained and saved Linear Regression model.")
        return self.lr_model

    def train_random_forest(self, X_train, y_train):
        self.rf_model = RandomForestRegressor(n_estimators=200, max_depth=15, min_samples_split=5, random_state=42)
        self.rf_model.fit(X_train, y_train)
        joblib.dump(self.rf_model, self.rf_path)
        logger.info("Trained and saved Random Forest model.")
        return self.rf_model

    def train_decision_tree(self, X_train, y_train_labels):
        self.dt_model = DecisionTreeClassifier(random_state=42)
        self.dt_model.fit(X_train, y_train_labels)
        joblib.dump(self.dt_model, self.dt_path)
        logger.info("Trained and saved Decision Tree model.")
        return self.dt_model

    def train_sarima(self, time_series_data):
        # time_series_data should be a pandas Series of CO2 values with hourly freq
        # SARIMA(1,1,1)(1,1,1,24) for hourly data with daily seasonality
        model = SARIMAX(time_series_data, order=(1,1,1), seasonal_order=(1,1,1,24))
        self.sarima_model = model.fit(disp=False)
        joblib.dump(self.sarima_model, self.sarima_path)
        logger.info("Trained and saved SARIMA model.")
        return self.sarima_model

    def predict_rf_with_confidence(self, X):
        if not self.rf_model:
            self.load_models()
        if not self.rf_model:
            raise Exception("Random Forest model not loaded.")
        
        preds = []
        for estimator in self.rf_model.estimators_:
            preds.append(estimator.predict(X))
        
        preds = np.array(preds)
        mean_pred = np.mean(preds, axis=0)
        conf_low = np.percentile(preds, 5, axis=0)
        conf_high = np.percentile(preds, 95, axis=0)
        
        return mean_pred, conf_low, conf_high
        
    def classify_zone(self, co2_value):
        # 0=Low (<400ppm), 1=Moderate (400-450), 2=High (450-500), 3=Critical (>500)
        if co2_value < 400:
            return 0
        elif co2_value < 450:
            return 1
        elif co2_value < 500:
            return 2
        else:
            return 3
