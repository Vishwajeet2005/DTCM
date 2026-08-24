"""
scripts/train_models.py - Digital Twin CO2 Monitor (DTCM)
==========================================================
Standalone training script that:

1. Bootstraps ``sys.path`` so the project root is importable.
2. Reads ``DATABASE_URL`` from the project Config.
3. Runs the full data-preprocessing pipeline to build feature matrix X and
   target vector y.
4. Splits data 70 / 15 / 15 (train / val / test) in *time order* (no shuffle).
5. Trains LinearRegression, RandomForestRegressor, DecisionTreeClassifier and
   - optionally - SARIMA.
6. Evaluates each model on the test split and applies the R- deployment gate.
7. Saves all models as .pkl files under the ``models/`` directory.
8. Prints a consolidated metrics table.

Usage
-----
    python scripts/train_models.py

Environment variables (loaded via python-dotenv)
-------------------------------------------------
    DATABASE_URL - SQLAlchemy connection string (defaults to SQLite DTCM DB)
    MODELS_DIR   - override default models directory (default: models/)
    LOG_LEVEL    - Python logging level (default: INFO)
"""

import sys
import os
import logging

# ---------------------------------------------------------------------------
# Bootstrap: make sure the project root (one level up from scripts/) is on
# the Python module search path so we can import app, config, ml, etc.
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Standard library / third-party imports (after path fix)
# ---------------------------------------------------------------------------
import traceback
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from config import Config  # type: ignore[import]
from ml.models import ModelManager, FEATURE_COLS
from ml.evaluate import ModelEvaluator

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
os.makedirs(os.path.join(_PROJECT_ROOT, "logs"), exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(_PROJECT_ROOT, "logs", "app.log"), encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("dtcm.train")


# ---------------------------------------------------------------------------
# Helper: data loading
# ---------------------------------------------------------------------------

def load_data() -> tuple[np.ndarray, np.ndarray]:
    """Load and preprocess data from the database.

    Attempts to import and run ``DataPreprocessor.full_pipeline``.  If that
    module is not yet available, falls back to generating a synthetic dataset
    so the training script can still be exercised end-to-end.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(X, y)`` where X has shape ``(n, len(FEATURE_COLS))`` and y shape
        ``(n,)``.
    """
    # --- Try the real DataPreprocessor first --------------------------------
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(Config.DATABASE_URL, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            from data.preprocessing import DataPreprocessor  # type: ignore[import]
            logger.info("Running DataPreprocessor.full_pipeline() -")
            preprocessor = DataPreprocessor()
            X, y = preprocessor.full_pipeline(session, fit_scaler=True)
            logger.info(
                "Preprocessing complete: X=%s  y=%s", X.shape, y.shape
            )
            return X, y
        except ImportError:
            logger.warning(
                "data.preprocessing not found - falling back to synthetic data."
            )
        finally:
            session.close()

    except Exception as exc:  # noqa: BLE001
        logger.warning("Database / preprocessor unavailable (%s) - using synthetic data.", exc)

    # --- Synthetic data fallback -------------------------------------------
    return _generate_synthetic_data()


def _generate_synthetic_data() -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic CO2 sensor data for offline model training / testing.

    Produces a realistic 6-month hourly dataset with diurnal and seasonal
    patterns plus Gaussian noise.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(X, y)`` - feature matrix and CO2 targets (ppm).
    """
    rng = np.random.default_rng(42)
    n = 24 * 30 * 6  # - 6 months of hourly data

    hours = np.arange(n)
    # Diurnal CO2 pattern: peaks around midday, lower at night
    co2_base = (
        420
        + 40 * np.sin(2 * np.pi * (hours % 24) / 24 - np.pi / 2)
        + 20 * np.sin(2 * np.pi * hours / (24 * 365))   # seasonal drift
        + rng.normal(0, 8, n)                             # sensor noise
    )
    co2_1h_avg = pd.Series(co2_base).rolling(1, min_periods=1).mean().values

    temperature = 20 + 10 * np.sin(2 * np.pi * (hours % 24) / 24) + rng.normal(0, 1, n)
    humidity    = 55 + 20 * np.cos(2 * np.pi * (hours % 24) / 24) + rng.normal(0, 2, n)
    pm25        = np.abs(30 + 15 * np.sin(2 * np.pi * (hours % 24) / 24) + rng.normal(0, 3, n))
    traffic     = np.abs(0.4 + 0.3 * np.sin(2 * np.pi * (hours % 24) / 24) + rng.normal(0, 0.05, n))

    hour_angle  = 2 * np.pi * (hours % 24) / 24
    month_angle = 2 * np.pi * (hours % (24 * 30)) / (24 * 30)

    X = np.column_stack([
        co2_1h_avg,
        temperature,
        humidity,
        pm25,
        traffic,
        np.sin(hour_angle),
        np.cos(hour_angle),
        np.sin(month_angle),
        np.cos(month_angle),
    ])
    y = co2_base  # target: raw CO2 ppm

    logger.info("Synthetic dataset generated: X=%s  y=%s", X.shape, y.shape)
    return X, y


# ---------------------------------------------------------------------------
# Helper: time-ordered train / val / test split
# ---------------------------------------------------------------------------

def time_split(
    X: np.ndarray, y: np.ndarray, train_frac: float = 0.70, val_frac: float = 0.15
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split arrays into train / validation / test preserving temporal order.

    Parameters
    ----------
    X, y:
        Feature matrix and target vector (time-ordered, oldest first).
    train_frac:
        Fraction of data for training (default 0.70).
    val_frac:
        Fraction of data for validation (default 0.15).
        The remaining ``1 - train_frac - val_frac`` is used for testing.

    Returns
    -------
    tuple
        ``(X_train, X_val, X_test, y_train, y_val, y_test)``
    """
    n = len(X)
    i_train = int(n * train_frac)
    i_val   = int(n * (train_frac + val_frac))

    X_train, y_train = X[:i_train],  y[:i_train]
    X_val,   y_val   = X[i_train:i_val], y[i_train:i_val]
    X_test,  y_test  = X[i_val:],    y[i_val:]

    logger.info(
        "Split sizes - train: %d  val: %d  test: %d", len(X_train), len(X_val), len(X_test)
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def main() -> None:
    """End-to-end model training pipeline entry point."""
    print("\n" + "=" * 70)
    print("  DTCM - Model Training Pipeline")
    print("=" * 70)

    # Resolve paths relative to project root
    models_dir = os.environ.get(
        "MODELS_DIR", os.path.join(_PROJECT_ROOT, "models")
    )
    log_path = os.path.join(_PROJECT_ROOT, "logs", "training_log.json")

    manager   = ModelManager(models_dir=models_dir)
    evaluator = ModelEvaluator(min_r2=0.80, log_path=log_path)
    all_metrics: dict[str, dict] = {}

    # ------------------------------------------------------------------ #
    # 1. Load data                                                         #
    # ------------------------------------------------------------------ #
    print("\n[1/5] Loading and preprocessing data -")
    X, y = load_data()

    # ------------------------------------------------------------------ #
    # 2. Time-ordered split                                                #
    # ------------------------------------------------------------------ #
    print("[2/5] Splitting data (70 / 15 / 15) -")
    X_train, X_val, X_test, y_train, y_val, y_test = time_split(X, y)

    # ------------------------------------------------------------------ #
    # 3. Train all models                                                  #
    # ------------------------------------------------------------------ #
    print("[3/5] Training models -\n")

    # 3a. Linear Regression
    print("  ? LinearRegression")
    manager.train_linear_regression(X_train, y_train)

    # 3b. Random Forest
    print("  ? RandomForestRegressor")
    manager.train_random_forest(X_train, y_train)

    # 3c. Decision Tree (classifier - bins y first)
    print("  ? DecisionTreeClassifier")
    manager.train_decision_tree(X_train, y_train)

    # 3d. SARIMA (optional - may fail if statsmodels absent or data too small)
    print("  ? SARIMA(1,1,1)(1,1,1,24)  [optional]")
    try:
        ts = pd.Series(y_train)
        manager.train_sarima(ts)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SARIMA training skipped: %s", exc)

    # ------------------------------------------------------------------ #
    # 4. Evaluate on test split                                            #
    # ------------------------------------------------------------------ #
    print("\n[4/5] Evaluating on test set -\n")

    # --- Linear Regression ---
    if manager.lr_model is not None:
        lr_pred = manager.lr_model.predict(X_test)
        lr_metrics = evaluator.evaluate_regression("LinearRegression", y_test, lr_pred)
        all_metrics["LinearRegression"] = lr_metrics
        evaluator.check_deployment_gate(lr_metrics)

    # --- Random Forest ---
    if manager.rf_model is not None:
        rf_pred = manager.rf_model.predict(X_test)
        rf_metrics = evaluator.evaluate_regression("RandomForest", y_test, rf_pred)
        all_metrics["RandomForest"] = rf_metrics
        evaluator.check_deployment_gate(rf_metrics)
        # Store R2 on manager for downstream use
        manager.r2_scores["RandomForest"] = rf_metrics["r2"]

    # --- Decision Tree (classification - we report accuracy-proxy via RMSE) ---
    if manager.dt_model is not None:
        # Predict zone classes and convert back to midpoint ppm for regression metrics
        zone_midpoints = {0: 350.0, 1: 425.0, 2: 475.0, 3: 550.0}
        dt_classes = manager.dt_model.predict(X_test)
        dt_pred_ppm = np.array([zone_midpoints[int(c)] for c in dt_classes])
        dt_metrics = evaluator.evaluate_regression(
            "DecisionTree (zone proxy)", y_test, dt_pred_ppm
        )
        all_metrics["DecisionTree (zone proxy)"] = dt_metrics
        # No deployment gate for classifier - it is not a primary forecaster.

    # --- SARIMA (in-sample residual on validation) ---
    if manager.sarima_model is not None:
        try:
            val_steps = len(y_val)
            sarima_pred = manager.sarima_model.forecast(steps=val_steps)
            sarima_arr  = np.asarray(sarima_pred)
            # Clip to sane range to avoid extreme synthetic outliers
            sarima_arr  = np.clip(sarima_arr, 200, 2000)
            sarima_metrics = evaluator.evaluate_regression(
                "SARIMA (val set)", y_val, sarima_arr
            )
            all_metrics["SARIMA (val set)"] = sarima_metrics
        except Exception as exc:  # noqa: BLE001
            logger.warning("SARIMA evaluation skipped: %s", exc)

    # ------------------------------------------------------------------ #
    # 5. Save models                                                       #
    # ------------------------------------------------------------------ #
    print("\n[5/5] Saving models -")

    save_map = [
        (manager.lr_model,     "lr_model.pkl"),
        (manager.rf_model,     "rf_model.pkl"),
        (manager.dt_model,     "dt_model.pkl"),
        (manager.sarima_model, "sarima_model.pkl"),
    ]
    for model_obj, fname in save_map:
        if model_obj is not None:
            manager.save_model(model_obj, fname)
            print(f"  Saved ? {os.path.join(models_dir, fname)}")
        else:
            print(f"  Skipped (not trained): {fname}")

    # Also save scaler if DataPreprocessor set one up
    scaler_src = os.path.join(_PROJECT_ROOT, "models", "scaler.pkl")
    if os.path.isfile(scaler_src):
        print(f"  Scaler already at: {scaler_src}")

    # ------------------------------------------------------------------ #
    # Final summary                                                        #
    # ------------------------------------------------------------------ #
    evaluator.print_metrics_table(all_metrics)
    print("Training pipeline complete.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")
        sys.exit(0)
    except Exception:  # noqa: BLE001
        logger.error("Unhandled exception during training:\n%s", traceback.format_exc())
        sys.exit(1)

