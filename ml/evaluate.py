"""
ml/evaluate.py --- Digital Twin CO2 Monitor (DTCM)
=================================================
ModelEvaluator: computes regression metrics, gates deployment decisions and
maintains a persistent JSON training log.

Deployment gate
---------------
A model must achieve R-- --- ``min_r2`` (default 0.80) on the held-out test set
to be considered ready for production.  The ``check_deployment_gate`` method
returns a boolean and emits a human-readable verdict so the training script
can decide whether to proceed.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Compute, log and gate ML model quality metrics.

    Parameters
    ----------
    min_r2:
        Minimum acceptable R-- score for the deployment gate (default 0.80).
    log_path:
        Absolute or relative path to the JSON training-log file.
        Parent directories are created automatically.
    """

    def __init__(
        self,
        min_r2: float = 0.80,
        log_path: str = "logs/training_log.json",
    ) -> None:
        self.min_r2 = min_r2
        self.log_path = log_path

        # Ensure the log directory exists at construction time.
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------

    def evaluate_regression(
        self,
        model_name: str,
        y_true: Any,
        y_pred: Any,
    ) -> dict:
        """Compute standard regression metrics and persist them to the log.

        Metrics computed
        ----------------
        * R--   --- coefficient of determination (higher is better, max 1.0)
        * MAE  --- mean absolute error (ppm)
        * MSE  --- mean squared error (ppm--)
        * RMSE --- root mean squared error (ppm)

        Parameters
        ----------
        model_name:
            Human-readable model identifier used in logs and tables.
        y_true:
            Ground-truth CO2 values (array-like).
        y_pred:
            Model predictions (array-like, same shape as ``y_true``).

        Returns
        -------
        dict
            ``{"model": str, "r2": float, "mae": float,
               "mse": float, "rmse": float}``
        """
        y_true_arr = np.asarray(y_true, dtype=float)
        y_pred_arr = np.asarray(y_pred, dtype=float)

        r2 = float(r2_score(y_true_arr, y_pred_arr))
        mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
        mse = float(mean_squared_error(y_true_arr, y_pred_arr))
        rmse = float(np.sqrt(mse))

        metrics = {
            "model": model_name,
            "r2": round(r2, 6),
            "mae": round(mae, 4),
            "mse": round(mse, 4),
            "rmse": round(rmse, 4),
        }

        logger.info(
            "[%s] R--=%.4f  MAE=%.4f  RMSE=%.4f", model_name, r2, mae, rmse
        )

        # Persist to the rolling training log
        self.log_training_run(metrics)

        return metrics

    # ------------------------------------------------------------------
    # Deployment gate
    # ------------------------------------------------------------------

    def check_deployment_gate(self, metrics: dict) -> bool:
        """Evaluate whether a model meets the R-- deployment threshold.

        Parameters
        ----------
        metrics:
            Dict as returned by :meth:`evaluate_regression`, must contain
            ``"model"`` and ``"r2"`` keys.

        Returns
        -------
        bool
            ``True`` if ``metrics["r2"] >= self.min_r2``, ``False`` otherwise.

        Side Effects
        ------------
        Prints a PASS / FAIL verdict to stdout and emits a logger warning on
        failure.
        """
        model_name = metrics.get("model", "<unknown>")
        r2 = metrics.get("r2", float("-inf"))
        gate_passed = r2 >= self.min_r2

        if gate_passed:
            print(
                f"  [PASS]  DEPLOYMENT GATE PASSED  [{model_name}]  "
                f"R2={r2:.4f} >= {self.min_r2:.2f}"
            )
        else:
            msg = (
                f"  [FAIL]  DEPLOYMENT GATE FAILED  [{model_name}]  "
                f"R2={r2:.4f} < {self.min_r2:.2f}  "
                f"- model NOT ready for production."
            )
            print(msg)
            logger.warning(msg)

        return gate_passed

    # ------------------------------------------------------------------
    # Persistent training log
    # ------------------------------------------------------------------

    def log_training_run(self, results: dict) -> None:
        """Append a timestamped training-run record to the JSON log file.

        The file contains a JSON array; each element is one training run.
        The file is created if it does not yet exist.

        Parameters
        ----------
        results:
            Arbitrary dict of metrics / metadata to store.
        """
        record = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            **results,
        }

        # Read existing log (or start fresh)
        existing: list[dict] = []
        if os.path.isfile(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as fh:
                    existing = json.load(fh)
                if not isinstance(existing, list):
                    # Corrupt or unexpected format --- reset
                    logger.warning(
                        "Training log at %s is not a JSON array; resetting.",
                        self.log_path,
                    )
                    existing = []
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read training log (%s); resetting.", exc)
                existing = []

        existing.append(record)

        try:
            with open(self.log_path, "w", encoding="utf-8") as fh:
                json.dump(existing, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Failed to write training log: %s", exc)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_metrics_table(self, all_metrics: dict) -> None:
        """Print a formatted ASCII table of metrics for all evaluated models.

        Parameters
        ----------
        all_metrics:
            Mapping of ``model_name --- metrics_dict`` as returned by
            :meth:`evaluate_regression`.  Each inner dict must contain at least
            the keys ``r2``, ``mae``, ``mse``, ``rmse``.
        """
        if not all_metrics:
            print("No metrics to display.")
            return

        header_fmt = "{:<28} {:>10} {:>12} {:>14} {:>12}"
        row_fmt    = "{:<28} {:>10.4f} {:>12.4f} {:>14.4f} {:>12.4f}"
        separator  = "-" * 80

        print("\n" + separator)
        print("  DTCM - Model Evaluation Summary")
        print(separator)
        print(header_fmt.format("Model", "R2", "MAE (ppm)", "MSE (ppm^2)", "RMSE (ppm)"))
        print(separator)

        for name, m in all_metrics.items():
            print(
                row_fmt.format(
                    name,
                    m.get("r2", float("nan")),
                    m.get("mae", float("nan")),
                    m.get("mse", float("nan")),
                    m.get("rmse", float("nan")),
                )
            )

        print(separator + "\n")

