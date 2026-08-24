"""
preprocessor.py
===============
DataPreprocessor class for the DTCM project.

Provides a full ML-ready pipeline:
    load -> missing-value handling -> outlier removal ->
    feature engineering -> normalisation -> feature/target split.
"""

import logging
import math
import os
import pickle
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column groups
# ---------------------------------------------------------------------------
NORMALIZE_COLS = [
    "co2_level",
    "temperature",
    "humidity",
    "pm25",
    "aqi",
    "co2_1h_avg",
    "co2_6h_avg",
    "co2_24h_avg",
]

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

TARGET_COL = "co2_level"

# Outlier bounds
CO2_VALID_MIN, CO2_VALID_MAX = 350.0, 5000.0
TEMP_VALID_MIN, TEMP_VALID_MAX = -20.0, 60.0

# AQI composite weights
AQI_COMPOSITE_MIN, AQI_COMPOSITE_MAX = 0.0, 500.0


class DataPreprocessor:
    """
    Full preprocessing pipeline for DTCM CO2 sensor data.

    Parameters
    ----------
    scaler_path : str
        Path to the saved MinMaxScaler pickle file (relative to CWD or absolute).
    """

    def __init__(self, scaler_path: str = "models/scaler.pkl") -> None:
        self.scaler_path = scaler_path
        self.scaler: Optional[MinMaxScaler] = None
        self._weather_warning_logged = False

    # ------------------------------------------------------------------
    # 1. Data Loading
    # ------------------------------------------------------------------
    def load_data_from_db(
        self,
        session: Session,
        start_date: Optional[pd.Timestamp] = None,
        end_date: Optional[pd.Timestamp] = None,
        sensor_ids: Optional[list] = None,
    ) -> pd.DataFrame:
        """
        Query EnvironmentalData from the database and return a raw DataFrame.

        Parameters
        ----------
        session    : SQLAlchemy session.
        start_date : Optional lower bound on timestamp (inclusive).
        end_date   : Optional upper bound on timestamp (inclusive).
        sensor_ids : Optional list of sensor IDs to include.

        Returns
        -------
        pd.DataFrame with columns matching EnvironmentalData model fields.
        """
        # Import here to avoid circular dependency at module level
        from db.models import EnvironmentalData  # type: ignore

        query = session.query(EnvironmentalData)

        if start_date is not None:
            query = query.filter(EnvironmentalData.timestamp >= start_date)
        if end_date is not None:
            query = query.filter(EnvironmentalData.timestamp <= end_date)
        if sensor_ids:
            query = query.filter(EnvironmentalData.sensor_id.in_(sensor_ids))

        # Stream into DataFrame without loading all ORM objects into memory
        rows = query.all()
        if not rows:
            logger.warning("load_data_from_db: no rows matched the query filters.")
            return pd.DataFrame()

        data = [
            {
                "id": r.id,
                "sensor_id": r.sensor_id,
                "timestamp": r.timestamp,
                "co2_level": r.co2_level,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "pm25": r.pm25,
                "aqi": r.aqi,
                "data_quality": r.data_quality,
                "data_gap": r.data_gap,
            }
            for r in rows
        ]
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        logger.info("Loaded %d rows from EnvironmentalData.", len(df))
        return df

    # ------------------------------------------------------------------
    # 2. Missing Value Handling
    # ------------------------------------------------------------------
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Impute missing sensor readings.

        Strategy
        --------
        * Sort by sensor_id and timestamp.
        * Within each sensor group, forward-fill gaps where consecutive
          readings are = 30 minutes apart.
        * For remaining NaN (larger gaps), apply column-wise mean imputation.

        Parameters
        ----------
        df : Raw DataFrame from load_data_from_db.

        Returns
        -------
        DataFrame with no NaN values in numeric columns.
        """
        if df.empty:
            return df

        df = df.sort_values(["sensor_id", "timestamp"]).copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        def _fill_group(group: pd.DataFrame) -> pd.DataFrame:
            """Forward-fill only within 30-min windows, then backfill."""
            group = group.set_index("timestamp").sort_index()

            # Build a mask: True where the gap to the *previous* row is = 30 min
            time_diff = group.index.to_series().diff().dt.total_seconds() / 60  # minutes
            # ffill only where gap is short (= 30 min) or it is the very first row
            for col in numeric_cols:
                if col == "sensor_id":
                    continue
                # Forward-fill then conditionally undo where gap was large
                ffilled = group[col].ffill()
                # Restore NaN where gap > 30 min (those positions get mean later)
                large_gap_mask = (time_diff > 30) & group[col].isna()
                group[col] = ffilled.where(~large_gap_mask, other=np.nan)

            group = group.reset_index()
            return group

        groups = []
        for _, grp in df.groupby("sensor_id", sort=False):
            groups.append(_fill_group(grp))

        df = pd.concat(groups, ignore_index=True)

        # Mean-impute any remaining NaNs (large gaps or first-row NaNs)
        for col in numeric_cols:
            if df[col].isna().any():
                col_mean = df[col].mean()
                filled_count = df[col].isna().sum()
                df[col] = df[col].fillna(col_mean)
                logger.debug(
                    "Mean-imputed %d NaN(s) in column '%s' with %.4f",
                    filled_count,
                    col,
                    col_mean,
                )

        return df.sort_values(["sensor_id", "timestamp"]).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 3. Outlier Removal
    # ------------------------------------------------------------------
    def remove_outliers(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Flag and separate outlier readings.

        A row is an outlier if:
            * co2_level < 350 or co2_level > 5000  ppm, OR
            * temperature < -20 or temperature > 60 -C

        Each outlier row is logged at WARNING level with sensor_id,
        timestamp, and the offending value(s).

        Parameters
        ----------
        df : Cleaned (missing-values handled) DataFrame.

        Returns
        -------
        (clean_df, outliers_df) : Both are DataFrames.
        """
        if df.empty:
            return df, pd.DataFrame()

        co2_outlier = (df["co2_level"] < CO2_VALID_MIN) | (
            df["co2_level"] > CO2_VALID_MAX
        )
        temp_outlier = (df["temperature"] < TEMP_VALID_MIN) | (
            df["temperature"] > TEMP_VALID_MAX
        )
        outlier_mask = co2_outlier | temp_outlier

        outliers_df = df[outlier_mask].copy()
        clean_df = df[~outlier_mask].copy()

        # Log each outlier
        for _, row in outliers_df.iterrows():
            logger.warning(
                "Outlier detected | sensor_id=%s | timestamp=%s | "
                "co2_level=%.2f | temperature=%.2f",
                row.get("sensor_id"),
                row.get("timestamp"),
                row.get("co2_level", float("nan")),
                row.get("temperature", float("nan")),
            )

        logger.info(
            "remove_outliers: %d clean rows, %d outlier rows.",
            len(clean_df),
            len(outliers_df),
        )
        return clean_df.reset_index(drop=True), outliers_df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # 4. Feature Engineering
    # ------------------------------------------------------------------
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Derive additional features from the cleaned sensor DataFrame.

        New columns
        -----------
        co2_1h_avg      : 1-hour rolling mean of co2_level per sensor.
        co2_6h_avg      : 6-hour rolling mean of co2_level per sensor.
        co2_24h_avg     : 24-hour rolling mean of co2_level per sensor.
        hour_sin        : sin(2p * hour / 24) cyclical encoding.
        hour_cos        : cos(2p * hour / 24) cyclical encoding.
        day_sin         : sin(2p * day_of_year / 365).
        day_cos         : cos(2p * day_of_year / 365).
        month_sin       : sin(2p * month / 12).
        month_cos       : cos(2p * month / 12).
        traffic_density : synthetic rush-hour proxy.
        aqi_composite   : 0.05*co2_level + 0.5*pm25, clamped [0,500].
        """
        if df.empty:
            return df

        df = df.sort_values(["sensor_id", "timestamp"]).copy()
        df = df.set_index("timestamp")

        # ------- Rolling averages per sensor -------
        def _rolling(grp: pd.DataFrame, window: int) -> pd.Series:
            return (
                grp["co2_level"]
                .rolling(window=window, min_periods=1)
                .mean()
            )

        groups_idx = df.groupby("sensor_id", sort=False)
        df["co2_1h_avg"] = groups_idx.apply(lambda g: _rolling(g, 1)).reset_index(
            level=0, drop=True
        )
        df["co2_6h_avg"] = groups_idx.apply(lambda g: _rolling(g, 6)).reset_index(
            level=0, drop=True
        )
        df["co2_24h_avg"] = groups_idx.apply(lambda g: _rolling(g, 24)).reset_index(
            level=0, drop=True
        )

        df = df.reset_index()  # restore timestamp as column

        # ------- Cyclical time encodings -------
        hours = df["timestamp"].dt.hour
        day_of_year = df["timestamp"].dt.dayofyear
        month = df["timestamp"].dt.month

        df["hour_sin"] = np.sin(2 * math.pi * hours / 24)
        df["hour_cos"] = np.cos(2 * math.pi * hours / 24)
        df["day_sin"] = np.sin(2 * math.pi * day_of_year / 365)
        df["day_cos"] = np.cos(2 * math.pi * day_of_year / 365)
        df["month_sin"] = np.sin(2 * math.pi * month / 12)
        df["month_cos"] = np.cos(2 * math.pi * month / 12)

        # ------- Traffic density (synthetic rush-hour proxy) -------
        # Peaks at hours 8 (AM rush) and 17-18 (PM rush); formula:
        #   0.3 * |sin(p * hour / 12)| + 0.1
        df["traffic_density"] = (
            0.3 * np.abs(np.sin(math.pi * hours / 12)) + 0.1
        )

        # ------- AQI composite -------
        df["aqi_composite"] = (0.05 * df["co2_level"] + 0.5 * df["pm25"]).clip(
            AQI_COMPOSITE_MIN, AQI_COMPOSITE_MAX
        )

        logger.info("engineer_features: added 12 new feature columns.")
        return df

    # ------------------------------------------------------------------
    # 5. Normalisation
    # ------------------------------------------------------------------
    def normalize(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Apply MinMaxScaler to the numeric feature columns.

        Parameters
        ----------
        df  : Feature-engineered DataFrame.
        fit : If True, fit scaler on *df* and persist to scaler_path.
              If False, load existing scaler and transform only.

        Returns
        -------
        DataFrame with NORMALIZE_COLS replaced by their scaled values.
        """
        if df.empty:
            return df

        # Only scale columns that are actually present in the DataFrame
        cols_present = [c for c in NORMALIZE_COLS if c in df.columns]

        if fit:
            self.scaler = MinMaxScaler()
            df[cols_present] = self.scaler.fit_transform(df[cols_present])
            # Persist scaler
            os.makedirs(os.path.dirname(os.path.abspath(self.scaler_path)), exist_ok=True)
            with open(self.scaler_path, "wb") as f:
                pickle.dump(self.scaler, f)
            logger.info("Scaler fitted and saved to '%s'.", self.scaler_path)
        else:
            if self.scaler is None:
                # Load from disk
                if not os.path.exists(self.scaler_path):
                    raise FileNotFoundError(
                        f"Scaler not found at '{self.scaler_path}'. "
                        "Run with fit=True first."
                    )
                with open(self.scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                logger.info("Scaler loaded from '%s'.", self.scaler_path)

            df[cols_present] = self.scaler.transform(df[cols_present])

        return df

    # ------------------------------------------------------------------
    # 6. Feature / Target Split
    # ------------------------------------------------------------------
    def prepare_features(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Produce the ML feature matrix X and target series y.

        Target: co2_level shifted by -1 (next hour's reading) per sensor group.
        Rows where the target is NaN (last row per sensor) are dropped.

        Parameters
        ----------
        df : Normalised, feature-engineered DataFrame.

        Returns
        -------
        (X, y) : X is a DataFrame of FEATURE_COLS; y is next-hour co2_level.
        """
        if df.empty:
            return pd.DataFrame(), pd.Series(dtype=float)

        df = df.sort_values(["sensor_id", "timestamp"]).copy()

        # Shift target within each sensor group so we don't leak across sensors
        df["target"] = df.groupby("sensor_id")["co2_level"].shift(-1)

        # Drop rows with no target (last row per sensor)
        df = df.dropna(subset=["target"])

        # Only keep FEATURE_COLS that exist
        available_features = [c for c in FEATURE_COLS if c in df.columns]
        missing = set(FEATURE_COLS) - set(available_features)
        if missing:
            logger.warning(
                "prepare_features: missing feature columns %s - they will be skipped.",
                missing,
            )

        X = df[available_features].reset_index(drop=True)
        y = df["target"].reset_index(drop=True)

        logger.info(
            "prepare_features: X shape %s, y shape %s.", X.shape, y.shape
        )
        return X, y

    # ------------------------------------------------------------------
    # 7. Full Pipeline
    # ------------------------------------------------------------------
    def full_pipeline(
        self,
        session: Session,
        fit_scaler: bool = True,
        start_date: Optional[pd.Timestamp] = None,
        end_date: Optional[pd.Timestamp] = None,
        sensor_ids: Optional[list] = None,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Run the complete preprocessing pipeline end-to-end.

        Steps
        -----
        1. load_data_from_db
        2. handle_missing_values
        3. remove_outliers  (outliers are discarded for ML)
        4. engineer_features
        5. normalize
        6. prepare_features

        Parameters
        ----------
        session     : Active SQLAlchemy session.
        fit_scaler  : Passed to normalize().
        start_date  : Passed to load_data_from_db().
        end_date    : Passed to load_data_from_db().
        sensor_ids  : Passed to load_data_from_db().

        Returns
        -------
        (X, y) ready for model training or inference.
        """
        logger.info("full_pipeline: starting.")

        df = self.load_data_from_db(
            session, start_date=start_date, end_date=end_date, sensor_ids=sensor_ids
        )
        if df.empty:
            logger.error("full_pipeline: no data loaded. Aborting pipeline.")
            return pd.DataFrame(), pd.Series(dtype=float)

        df = self.handle_missing_values(df)
        df, _ = self.remove_outliers(df)
        df = self.engineer_features(df)
        df = self.normalize(df, fit=fit_scaler)
        X, y = self.prepare_features(df)

        logger.info("full_pipeline: complete. X=%s, y=%s.", X.shape, y.shape)
        return X, y

