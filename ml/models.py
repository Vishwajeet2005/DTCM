"""
ml/models.py - Digital Twin CO2 Monitor (DTCM)
===============================================
ModelManager: trains, saves, loads and runs inference with scikit-learn and
SARIMA models used by the DTCM system.

Models managed
--------------
* LinearRegression    - baseline CO2 point forecast
* RandomForestRegressor - primary short-term forecast (with confidence bands)
* DecisionTreeClassifier - zone severity classification (4 classes)
* SARIMA(1,1,1)(1,1,1,24) - optional long-term seasonal forecast
"""

import os
import logging
import pickle
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature / label constants
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "co2_1h_avg",
    "temperature",
    "humidity",
    "pm25",
    "traffic_density",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
]

ZONE_LABELS = {0: "Low", 1: "Moderate", 2: "High", 3: "Critical"}

# Bins used to convert continuous CO2 ppm into ordinal severity classes:
#   0 - Low (<400), 1 - Moderate (400-450), 2 - High (450-500), 3 - Critical (>500)
CO2_BINS = [0, 400, 450, 500, float("inf")]


class ModelManager:
    """Central registry that trains, persists and serves DTCM ML models.

    Attributes
    ----------
    models_dir : str
        Directory where serialised model .pkl files are stored.
    lr_model : LinearRegression | None
        Trained linear regression model.
    rf_model : RandomForestRegressor | None
        Trained random-forest regressor.
    dt_model : DecisionTreeClassifier | None
        Trained decision-tree zone classifier.
    sarima_model : object | None
        Fitted statsmodels SARIMAX result, or None if unavailable.
    r2_scores : dict
        Holds R2 scores keyed by model name, populated after evaluation.
    """

    def __init__(self, models_dir: str = "models") -> None:
        """Initialise ModelManager and ensure the model directory exists.

        Parameters
        ----------
        models_dir:
            Path (absolute or relative) to the directory that holds .pkl files.
        """
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)

        self.lr_model: Optional[LinearRegression] = None
        self.rf_model: Optional[RandomForestRegressor] = None
        self.dt_model: Optional[DecisionTreeClassifier] = None
        self.sarima_model = None  # statsmodels SARIMAXResultsWrapper
        self.r2_scores: dict = {}

    # ------------------------------------------------------------------
    # Training helpers
    # ------------------------------------------------------------------

    def train_linear_regression(
        self, X_train: np.ndarray, y_train: np.ndarray
    ) -> LinearRegression:
        """Fit a LinearRegression model and cache it on ``self.lr_model``.

        Parameters
        ----------
        X_train:
            Feature matrix (n_samples x n_features).
        y_train:
            Target CO2 values in ppm.

        Returns
        -------
        LinearRegression
            The fitted model instance.
        """
        logger.info("Training LinearRegression -")
        model = LinearRegression()
        model.fit(X_train, y_train)
        self.lr_model = model
        logger.info("LinearRegression training complete.")
        return model

    def train_random_forest(
        self, X_train: np.ndarray, y_train: np.ndarray
    ) -> RandomForestRegressor:
        """Fit a RandomForestRegressor and cache it on ``self.rf_model``.

        Hyper-parameters chosen to balance accuracy and inference speed for
        hourly CO2 data:
        * n_estimators = 200   - enough trees for stable variance estimates
        * max_depth    = 15    - prevents over-deep trees on noisy sensor data
        * min_samples_split = 5 - light regularisation

        Parameters
        ----------
        X_train:
            Feature matrix.
        y_train:
            Target CO2 values in ppm.

        Returns
        -------
        RandomForestRegressor
            The fitted model instance.
        """
        logger.info("Training RandomForestRegressor (n_estimators=200) -")
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1,  # use all available CPU cores
        )
        model.fit(X_train, y_train)
        self.rf_model = model
        logger.info("RandomForestRegressor training complete.")
        return model

    def train_decision_tree(
        self, X_train: np.ndarray, y_train: np.ndarray
    ) -> DecisionTreeClassifier:
        """Fit a DecisionTreeClassifier for 4-class zone severity.

        ``y_train`` is expected to contain continuous CO2 ppm values; this
        method bins them into ordinal classes (0-3) using ``CO2_BINS`` before
        fitting.

        Parameters
        ----------
        X_train:
            Feature matrix.
        y_train:
            Continuous CO2 ppm values (will be binned internally).

        Returns
        -------
        DecisionTreeClassifier
            The fitted classifier.
        """
        logger.info("Training DecisionTreeClassifier (zone severity) -")

        # Convert continuous CO2 into 4-class labels
        y_classes = self._bin_co2(pd.Series(y_train))

        model = DecisionTreeClassifier(
            max_depth=10,
            min_samples_split=10,
            random_state=42,
        )
        model.fit(X_train, y_classes)
        self.dt_model = model
        logger.info("DecisionTreeClassifier training complete.")
        return model

    def train_sarima(self, ts: pd.Series) -> object:
        """Fit SARIMA(1,1,1)(1,1,1,24) on an hourly CO2 time series.

        statsmodels is imported inside the method so that the rest of the
        module works even if it is not installed.

        Parameters
        ----------
        ts:
            Hourly CO2 ppm time-series (pd.Series), indexed by datetime.

        Returns
        -------
        SARIMAXResultsWrapper | None
            The fitted model result, or ``None`` on any failure.
        """
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore
        except ImportError:
            logger.warning(
                "statsmodels not installed - SARIMA training skipped."
            )
            return None

        try:
            logger.info("Fitting SARIMA(1,1,1)(1,1,1,24) -")
            model = SARIMAX(
                ts,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 24),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            result = model.fit(disp=False)
            self.sarima_model = result
            logger.info("SARIMA fitting complete.")
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("SARIMA fitting failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_short_term(
        self, X: pd.DataFrame, horizon_hours: int = 24
    ) -> dict:
        """Forecast CO2 for the next ``horizon_hours`` hours using the RF model.

        Uses *recursive* (autoregressive) multi-step forecasting:
        1. Predict step t+1 from the current feature row.
        2. Shift the feature row: update ``co2_1h_avg`` with the prediction,
           update cyclical time features for the next hour.
        3. Repeat until ``horizon_hours`` steps have been generated.

        Confidence intervals are derived from the spread of individual tree
        predictions (5th and 95th percentiles).

        Parameters
        ----------
        X:
            DataFrame containing one row (the latest feature snapshot).
        horizon_hours:
            Number of future hours to forecast.

        Returns
        -------
        dict
            Keys: ``predictions``, ``confidence_low``, ``confidence_high``,
            ``model_used``.
        """
        if self.rf_model is None:
            raise RuntimeError(
                "RandomForestRegressor is not trained. Call train_random_forest() first."
            )

        predictions: list[float] = []
        conf_low: list[float] = []
        conf_high: list[float] = []

        # Work on a mutable copy - keep only the feature columns present in
        # the training data (drop extras if caller passes more columns).
        available_cols = [c for c in FEATURE_COLS if c in X.columns]
        row = X[available_cols].iloc[0].copy()

        for step in range(horizon_hours):
            X_arr = row.values.reshape(1, -1)

            # Point prediction
            pred = float(self.rf_model.predict(X_arr)[0])
            predictions.append(pred)

            # Per-tree predictions for confidence interval
            low, high = self.get_rf_confidence(X_arr)
            conf_low.append(float(low[0]))
            conf_high.append(float(high[0]))

            # --- Recursive feature update ---
            # Update the rolling CO2 average with the newly predicted value.
            if "co2_1h_avg" in available_cols:
                row["co2_1h_avg"] = pred

            # Advance the hour-of-day cyclical features by one hour.
            # We track the current fractional hour angle and increment by 2p/24.
            if "hour_sin" in available_cols and "hour_cos" in available_cols:
                # Recover current hour angle from sin/cos, add 1h, re-encode.
                angle = np.arctan2(row["hour_sin"], row["hour_cos"])
                angle += 2 * np.pi / 24  # advance one hour
                row["hour_sin"] = np.sin(angle)
                row["hour_cos"] = np.cos(angle)

        return {
            "predictions": predictions,
            "confidence_low": conf_low,
            "confidence_high": conf_high,
            "model_used": "RandomForest",
        }

    def predict_long_term(
        self, X: pd.DataFrame, horizon_days: int = 7
    ) -> dict:
        """Forecast CO2 for ``horizon_days`` days (daily granularity).

        Strategy:
        * Primary forecast: RF recursive multi-step (hourly ? daily mean).
        * If SARIMA is available, blend RF and SARIMA 50/50 for smoother
          long-range predictions.

        Parameters
        ----------
        X:
            DataFrame with one row (latest feature snapshot).
        horizon_days:
            Number of future calendar days to forecast (default 7).

        Returns
        -------
        dict
            Keys: ``predictions``, ``confidence_low``, ``confidence_high``,
            ``model_used``.
        """
        if self.rf_model is None:
            raise RuntimeError(
                "RandomForestRegressor is not trained. Call train_random_forest() first."
            )

        horizon_hours = horizon_days * 24

        # Get hourly RF forecast
        rf_result = self.predict_short_term(X, horizon_hours=horizon_hours)
        rf_preds = np.array(rf_result["predictions"])
        rf_low = np.array(rf_result["confidence_low"])
        rf_high = np.array(rf_result["confidence_high"])

        # Aggregate to daily means
        def _daily_mean(arr: np.ndarray, days: int) -> list[float]:
            return [
                float(arr[d * 24 : (d + 1) * 24].mean())
                for d in range(days)
            ]

        daily_rf = np.array(_daily_mean(rf_preds, horizon_days))
        daily_low = np.array(_daily_mean(rf_low, horizon_days))
        daily_high = np.array(_daily_mean(rf_high, horizon_days))

        model_used = "RandomForest"

        if self.sarima_model is not None:
            try:
                # SARIMA forecast in ppm units, same horizon (hours)
                sarima_fc = self.sarima_model.forecast(steps=horizon_hours)
                sarima_preds = np.array(sarima_fc)
                daily_sarima = np.array(_daily_mean(sarima_preds, horizon_days))

                # 50/50 blend
                daily_rf = 0.5 * daily_rf + 0.5 * daily_sarima
                model_used = "RandomForest+SARIMA (blended)"
            except Exception as exc:  # noqa: BLE001
                logger.warning("SARIMA inference failed, using RF only: %s", exc)

        return {
            "predictions": daily_rf.tolist(),
            "confidence_low": daily_low.tolist(),
            "confidence_high": daily_high.tolist(),
            "model_used": model_used,
        }

    def classify_zones(self, X: pd.DataFrame) -> list[dict]:
        """Classify each sensor row into a CO2 zone severity class.

        Uses the trained DecisionTreeClassifier if available; falls back to
        rule-based binning on the raw ``co2_1h_avg`` (or ``co2_level``) feature
        column when the classifier is not yet loaded.

        Parameters
        ----------
        X:
            DataFrame where each row represents one sensor reading. Must
            contain at least the FEATURE_COLS columns, plus optionally a
            ``sensor_id`` column.

        Returns
        -------
        list[dict]
            One dict per row:
            ``{"sensor_id": ..., "zone_class": int, "label": str}``
        """
        results: list[dict] = []

        # Determine sensor IDs (use row index if no sensor_id column)
        sensor_ids = (
            X["sensor_id"].tolist()
            if "sensor_id" in X.columns
            else list(range(len(X)))
        )

        if self.dt_model is not None:
            # Use trained classifier
            available_cols = [c for c in FEATURE_COLS if c in X.columns]
            X_arr = X[available_cols].values
            classes = self.dt_model.predict(X_arr).tolist()
        else:
            # Fallback: rule-based binning using CO2 value directly
            logger.warning(
                "DecisionTreeClassifier not loaded - using rule-based fallback."
            )
            co2_col = "co2_1h_avg" if "co2_1h_avg" in X.columns else "co2_level"
            classes = self._bin_co2(X[co2_col]).tolist()

        for sid, cls in zip(sensor_ids, classes):
            results.append(
                {
                    "sensor_id": sid,
                    "zone_class": int(cls),
                    "label": ZONE_LABELS.get(int(cls), "Unknown"),
                }
            )

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_model(self, model: object, filename: str) -> None:
        """Serialise ``model`` to ``<models_dir>/<filename>`` using pickle.

        Parameters
        ----------
        model:
            Any picklable Python object (sklearn estimator, SARIMAX result-).
        filename:
            Target filename inside ``self.models_dir``, e.g. ``rf_model.pkl``.
        """
        path = os.path.join(self.models_dir, filename)
        with open(path, "wb") as fh:
            pickle.dump(model, fh, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("Model saved ? %s", path)

    def load_all_models(self) -> None:
        """Load all recognised .pkl files from ``models_dir`` into instance attributes.

        Expected filenames
        ------------------
        * ``lr_model.pkl``      ? ``self.lr_model``
        * ``rf_model.pkl``      ? ``self.rf_model``
        * ``dt_model.pkl``      ? ``self.dt_model``
        * ``sarima_model.pkl``  ? ``self.sarima_model``

        Unknown .pkl files are silently ignored.
        """
        mapping = {
            "lr_model.pkl": "lr_model",
            "rf_model.pkl": "rf_model",
            "dt_model.pkl": "dt_model",
            "sarima_model.pkl": "sarima_model",
        }
        for filename, attr in mapping.items():
            path = os.path.join(self.models_dir, filename)
            if os.path.isfile(path):
                try:
                    with open(path, "rb") as fh:
                        setattr(self, attr, pickle.load(fh))
                    logger.info("Loaded %s from %s", attr, path)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Failed to load %s: %s", path, exc)
            else:
                logger.debug("Model file not found (skipping): %s", path)

    # ------------------------------------------------------------------
    # Confidence interval helper
    # ------------------------------------------------------------------

    def get_rf_confidence(
        self, X: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute 5th / 95th percentile prediction bands from the RF ensemble.

        Collects one prediction per decision tree in the forest, then takes
        column-wise percentiles to produce lower and upper confidence bounds.

        Parameters
        ----------
        X:
            2-D numpy array, shape ``(n_samples, n_features)``.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(low, high)`` arrays each of shape ``(n_samples,)``.

        Raises
        ------
        RuntimeError
            If ``self.rf_model`` has not been trained yet.
        """
        if self.rf_model is None:
            raise RuntimeError(
                "RandomForestRegressor is not trained."
            )

        # Stack per-tree predictions: shape (n_estimators, n_samples)
        tree_preds = np.array(
            [tree.predict(X) for tree in self.rf_model.estimators_]
        )
        low = np.percentile(tree_preds, 5, axis=0)   # 5th percentile
        high = np.percentile(tree_preds, 95, axis=0)  # 95th percentile
        return low, high

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bin_co2(co2_series: pd.Series) -> pd.Series:
        """Bin continuous CO2 ppm values into 4 ordinal zone classes (0-3).

        Parameters
        ----------
        co2_series:
            Pandas Series of CO2 ppm values.

        Returns
        -------
        pd.Series
            Integer series: 0=Low, 1=Moderate, 2=High, 3=Critical.
        """
        return pd.cut(
            co2_series,
            bins=CO2_BINS,
            labels=[0, 1, 2, 3],
            right=True,
        ).astype(int)

