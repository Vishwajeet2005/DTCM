"""
tests/test_preprocessing.py --- Digital Twin CO--- Monitor (DTCM)
==============================================================
Unit tests for :mod:`processing.preprocessor.DataPreprocessor`.

All tests operate directly on synthetic pandas DataFrames; no database or
Flask application context is required, making the suite extremely fast.

Tested behaviours
-----------------
1. Short-gap forward-fill imputation (---30 min gap --- ffill).
2. Long-gap mean imputation (>60 min gap --- column mean).
3. Outlier removal: CO--- too high (> 5000 ppm) flagged as outlier.
4. Outlier removal: CO--- too low (< 250 ppm) flagged as outlier.
5. Feature engineering: cyclical time encoding columns present.
6. Normalisation: all feature columns scaled to [0, 1].
7. Rolling averages: 1 h, 6 h, 24 h window columns exist.
8. prepare_features() shape: X has FEATURE_COLS, y is a Series.
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
import pytest

from ml.models import FEATURE_COLS
from processing.preprocessor import DataPreprocessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_df(n: int = 120, co2_base: float = 420.0) -> pd.DataFrame:
    """Build a minimal EnvironmentalData-shaped DataFrame with *n* hourly rows.

    Args:
        n: Number of rows (hours).
        co2_base: Base CO--- ppm value; small random noise is added per row.

    Returns:
        A :class:`pandas.DataFrame` with columns matching the DB schema.
    """
    rng = np.random.default_rng(seed=0)
    now = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    timestamps = [now - datetime.timedelta(hours=n - i) for i in range(n)]

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "sensor_id": 1,
            "co2_level": co2_base + rng.uniform(-10, 10, n),
            "temperature": 22.0 + rng.uniform(-3, 3, n),
            "humidity": 55.0 + rng.uniform(-10, 10, n),
            "pm25": 10.0 + rng.uniform(0, 5, n),
            "aqi": 60.0 + rng.uniform(-5, 5, n),
            "traffic_density": rng.uniform(0, 100, n),
        }
    )


# ---------------------------------------------------------------------------
# 1. Short-gap forward-fill
# ---------------------------------------------------------------------------


class TestMissingValueHandlingShortGap:
    """Test that a ---30-min gap is handled by forward-fill."""

    def test_missing_value_handling_short_gap(self) -> None:
        """Two rows with a 15-min gap should be forward-filled, not mean-imputed."""
        dp = DataPreprocessor()

        # Build a small DataFrame with a deliberate NaN in the middle
        df = _make_df(n=30)
        # Introduce a 15-min gap by setting co2_level to NaN at row 10
        df.loc[10, "co2_level"] = np.nan

        result = dp.handle_missing_values(df.copy())

        # After forward-fill the NaN should be replaced with the row-9 value
        assert result["co2_level"].isna().sum() == 0, (
            "Forward-fill should eliminate all NaNs in a short-gap scenario."
        )
        # The imputed value must equal the preceding row's value (ffill)
        assert result.loc[10, "co2_level"] == pytest.approx(
            df.loc[9, "co2_level"], rel=1e-6
        ), "Short-gap imputation must use the previous valid observation (ffill)."


# ---------------------------------------------------------------------------
# 2. Long-gap mean imputation
# ---------------------------------------------------------------------------


class TestMissingValueHandlingLongGap:
    """Test that a >60-min gap falls back to column-mean imputation."""

    def test_missing_value_handling_long_gap(self) -> None:
        """Rows with a 2-hour gap should be imputed with the column mean."""
        dp = DataPreprocessor()

        df = _make_df(n=50)
        # Create a 2-hour gap by blanking several consecutive rows
        gap_indices = [20, 21, 22]
        df.loc[gap_indices, "co2_level"] = np.nan

        result = dp.handle_missing_values(df.copy())

        assert result["co2_level"].isna().sum() == 0, (
            "Mean imputation should eliminate all NaNs in a long-gap scenario."
        )
        # Mean-imputed value should be close to the column mean of the non-NaN rows
        expected_mean = df["co2_level"].dropna().mean()
        for idx in gap_indices:
            assert result.loc[idx, "co2_level"] == pytest.approx(
                expected_mean, rel=0.1
            ), f"Row {idx} should be imputed near the column mean."


# ---------------------------------------------------------------------------
# 3 & 4. Outlier removal
# ---------------------------------------------------------------------------


class TestOutlierRemoval:
    """Test that physically implausible CO--- readings are flagged as outliers."""

    def test_outlier_removal_co2_too_high(self) -> None:
        """A CO--- reading of 6000 ppm must be excluded from the clean DataFrame."""
        dp = DataPreprocessor()
        df = _make_df(n=60)

        # Plant an impossible reading
        df.loc[30, "co2_level"] = 6000.0

        clean_df, outliers_df = dp.remove_outliers(df.copy())

        assert 30 not in clean_df.index, (
            "Row with CO---=6000 ppm should NOT appear in clean_df."
        )
        assert len(outliers_df) >= 1, (
            "outliers_df must contain at least the CO---=6000 ppm row."
        )
        assert (outliers_df["co2_level"] == 6000.0).any(), (
            "The 6000-ppm value must be present in outliers_df."
        )

    def test_outlier_removal_co2_too_low(self) -> None:
        """A CO--- reading of 200 ppm must be excluded from the clean DataFrame."""
        dp = DataPreprocessor()
        df = _make_df(n=60)

        df.loc[15, "co2_level"] = 200.0

        clean_df, outliers_df = dp.remove_outliers(df.copy())

        assert 15 not in clean_df.index, (
            "Row with CO---=200 ppm should NOT appear in clean_df."
        )
        assert (outliers_df["co2_level"] == 200.0).any(), (
            "The 200-ppm value must be present in outliers_df."
        )


# ---------------------------------------------------------------------------
# 5. Feature engineering --- cyclical time encoding
# ---------------------------------------------------------------------------


class TestFeatureEngineeringTimeEncoding:
    """Test that cyclical hour and month features are computed correctly."""

    def test_feature_engineering_time_encoding(self) -> None:
        """hour_sin, hour_cos, month_sin, month_cos must exist and be in [-1, 1]."""
        dp = DataPreprocessor()
        df = _make_df(n=48)

        result = dp.engineer_features(df.copy())

        for col in ("hour_sin", "hour_cos", "month_sin", "month_cos"):
            assert col in result.columns, f"Column '{col}' is missing after feature engineering."
            assert result[col].between(-1.0, 1.0).all(), (
                f"Column '{col}' must contain values in [-1, 1]; "
                f"got range [{result[col].min():.4f}, {result[col].max():.4f}]."
            )


# ---------------------------------------------------------------------------
# 6. Normalisation
# ---------------------------------------------------------------------------


class TestNormalisationRange:
    """Test that normalise() scales all feature columns to [0, 1]."""

    def test_normalization_range(self) -> None:
        """After normalise(), every feature column value must be in [0, 1]."""
        dp = DataPreprocessor()
        df = _make_df(n=120)

        # Engineer features so the relevant columns exist
        df = dp.engineer_features(df.copy())
        # Add rolling averages
        df = dp.add_rolling_averages(df.copy())

        normalised = dp.normalize(df.copy())

        # Check only numeric columns that exist in the normalised output
        cols_to_check = [c for c in FEATURE_COLS if c in normalised.columns]
        assert len(cols_to_check) > 0, "No FEATURE_COLS found in normalised DataFrame."

        for col in cols_to_check:
            col_min = normalised[col].min()
            col_max = normalised[col].max()
            assert col_min >= -1e-9, (
                f"Column '{col}' min={col_min:.6f} is below 0 after normalisation."
            )
            assert col_max <= 1 + 1e-9, (
                f"Column '{col}' max={col_max:.6f} exceeds 1 after normalisation."
            )


# ---------------------------------------------------------------------------
# 7. Rolling averages
# ---------------------------------------------------------------------------


class TestRollingAverages:
    """Test that rolling-average columns are added by add_rolling_averages()."""

    def test_rolling_averages(self) -> None:
        """co2_1h_avg, co2_6h_avg, co2_24h_avg must exist after add_rolling_averages()."""
        dp = DataPreprocessor()
        df = _make_df(n=120)

        result = dp.add_rolling_averages(df.copy())

        for col in ("co2_1h_avg", "co2_6h_avg", "co2_24h_avg"):
            assert col in result.columns, (
                f"Column '{col}' is missing after add_rolling_averages()."
            )
            # Rolling values must not be entirely NaN (enough rows exist)
            non_null_count = result[col].notna().sum()
            assert non_null_count > 0, f"Column '{col}' is entirely NaN."


# ---------------------------------------------------------------------------
# 8. prepare_features() shape
# ---------------------------------------------------------------------------


class TestPrepareFeaturesShape:
    """Test that prepare_features() returns the correct X/y shapes."""

    def test_prepare_features_shape(self) -> None:
        """X must contain exactly FEATURE_COLS; y must be a pandas Series."""
        dp = DataPreprocessor()
        df = _make_df(n=200)

        # Run the full pre-processing pipeline before calling prepare_features
        df = dp.engineer_features(df.copy())
        df = dp.add_rolling_averages(df.copy())
        df.dropna(inplace=True)

        X, y = dp.prepare_features(df.copy())

        # y must be a Series
        assert isinstance(y, pd.Series), f"y should be pd.Series, got {type(y).__name__}."

        # X must contain at minimum the expected feature columns
        for col in FEATURE_COLS:
            assert col in X.columns, f"Feature column '{col}' missing from X."

        # Shapes must be consistent
        assert len(X) == len(y), (
            f"X ({len(X)} rows) and y ({len(y)} rows) must have the same length."
        )

