"""
db/models.py - SQLAlchemy ORM models for Digital Twin CO2 Monitor (DTCM).

All seven domain models are defined here and share the single ``db``
(SQLAlchemy) instance that is created in ``app.py`` and injected at
application-factory time.

Tables
------
* SensorData          - Physical sensor registry.
* EnvironmentalData   - Time-series CO2 and environmental readings.
* User                - Application users with role-based access control.
* PredictionResult    - ML model CO2 predictions with confidence intervals.
* SimulationResult    - Digital-twin scenario simulation outputs.
* Alert               - Threshold breach notifications.
* Threshold           - Per-sensor configurable alert thresholds.
"""

from __future__ import annotations

import datetime
from typing import Any

import bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ---------------------------------------------------------------------------
# Shared SQLAlchemy instance.
# Created here; initialised with the Flask app in app.py via db.init_app().
# ---------------------------------------------------------------------------
db: SQLAlchemy = SQLAlchemy()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _utcnow() -> datetime.datetime:
    """Return the current UTC datetime (timezone-naive for SQLite compat)."""
    return datetime.datetime.utcnow()


# ---------------------------------------------------------------------------
# 1. SensorData
# ---------------------------------------------------------------------------


class SensorData(db.Model):
    """Registry of physical CO2 sensors deployed across monitored zones.

    Attributes:
        sensor_id:         Auto-incrementing primary key.
        location:          Human-readable deployment location (max 255 chars).
        type:              Sensor hardware/model type (max 100 chars).
        installation_date: Date the sensor was commissioned.
        status:            Operational status; defaults to ``'Active'``.
    """

    __tablename__ = "SensorData"

    sensor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=True)
    installation_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active")

    # Relationships (back-references)
    environmental_data: Mapped[list["EnvironmentalData"]] = relationship(
        "EnvironmentalData", back_populates="sensor", lazy="dynamic"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the model instance to a JSON-safe dictionary."""
        return {
            "sensor_id": self.sensor_id,
            "location": self.location,
            "type": self.type,
            "installation_date": (
                self.installation_date.isoformat() if self.installation_date else None
            ),
            "status": self.status,
        }

    def __repr__(self) -> str:
        return f"<SensorData id={self.sensor_id} location={self.location!r}>"


# ---------------------------------------------------------------------------
# 2. EnvironmentalData
# ---------------------------------------------------------------------------


class EnvironmentalData(db.Model):
    """Time-series environmental readings captured from sensors.

    Attributes:
        data_id:    Auto-incrementing primary key.
        sensor_id:  FK to :class:`SensorData`.
        co2_level:  CO2 concentration in ppm (required).
        temperature:Ambient temperature in -C.
        humidity:   Relative humidity in %.
        pm25:       Particulate matter PM2.5 in -g/m-.
        aqi:        Air Quality Index.
        timestamp:  UTC datetime of the reading (auto-set on insert).
        data_gap:   Flag indicating synthetic/imputed value (default False).
    """

    __tablename__ = "EnvironmentalData"

    data_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("SensorData.sensor_id", ondelete="CASCADE"), nullable=False
    )
    co2_level: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    aqi: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    data_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_envdata_timestamp", "timestamp"),
        Index("ix_envdata_sensor_id", "sensor_id"),
    )

    # Relationships
    sensor: Mapped["SensorData"] = relationship("SensorData", back_populates="environmental_data")
    predictions: Mapped[list["PredictionResult"]] = relationship(
        "PredictionResult", back_populates="environmental_data", lazy="dynamic"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="environmental_data", lazy="dynamic"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the model instance to a JSON-safe dictionary."""
        return {
            "data_id": self.data_id,
            "sensor_id": self.sensor_id,
            "co2_level": self.co2_level,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pm25": self.pm25,
            "aqi": self.aqi,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "data_gap": self.data_gap,
        }

    def __repr__(self) -> str:
        return (
            f"<EnvironmentalData id={self.data_id} sensor={self.sensor_id} "
            f"co2={self.co2_level}>"
        )


# ---------------------------------------------------------------------------
# 3. User
# ---------------------------------------------------------------------------


class User(db.Model):
    """Application user with role-based access control.

    Valid roles: ``environmental_authority``, ``administrator``,
    ``researcher``, ``general``.

    Attributes:
        user_id:       Auto-incrementing primary key.
        name:          Display name.
        email:         Unique login e-mail address.
        role:          RBAC role string.
        password_hash: bcrypt hash (never returned via API).
        created_at:    UTC datetime of account creation.
    """

    __tablename__ = "Users"

    VALID_ROLES = frozenset(
        {"environmental_authority", "administrator", "researcher", "general"}
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )

    def set_password(self, password: str) -> None:
        """Hash *password* with bcrypt (cost factor 12) and store the hash.

        Args:
            password: Plain-text password supplied by the user.
        """
        # bcrypt.hashpw expects bytes; encode with utf-8 first.
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        self.password_hash = hashed.decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Verify *password* against the stored bcrypt hash.

        Args:
            password: Plain-text candidate password.

        Returns:
            True if the password matches, False otherwise.
        """
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the user to a JSON-safe dictionary.

        The ``password_hash`` field is intentionally excluded from the output.
        """
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.user_id} email={self.email!r} role={self.role!r}>"


# ---------------------------------------------------------------------------
# 4. PredictionResult
# ---------------------------------------------------------------------------


class PredictionResult(db.Model):
    """CO2 forecast produced by a trained ML model.

    Attributes:
        prediction_id:   Auto-incrementing primary key.
        data_id:         FK to the :class:`EnvironmentalData` row used as input.
        predicted_co2:   Forecasted CO2 level in ppm.
        model_used:      Name/version of the model that generated the forecast.
        confidence_low:  Lower bound of the 95 % prediction interval.
        confidence_high: Upper bound of the 95 % prediction interval.
        prediction_time: UTC datetime when the forecast was generated.
    """

    __tablename__ = "PredictionResults"

    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("EnvironmentalData.data_id", ondelete="SET NULL"),
        nullable=True,
    )
    predicted_co2: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )

    # Relationship
    environmental_data: Mapped["EnvironmentalData | None"] = relationship(
        "EnvironmentalData", back_populates="predictions"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the prediction to a JSON-safe dictionary."""
        return {
            "prediction_id": self.prediction_id,
            "data_id": self.data_id,
            "predicted_co2": self.predicted_co2,
            "model_used": self.model_used,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
            "prediction_time": (
                self.prediction_time.isoformat() if self.prediction_time else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"<PredictionResult id={self.prediction_id} "
            f"predicted={self.predicted_co2} model={self.model_used!r}>"
        )


# ---------------------------------------------------------------------------
# 5. SimulationResult
# ---------------------------------------------------------------------------


class SimulationResult(db.Model):
    """Digital-twin scenario simulation output.

    Attributes:
        sim_id:          Auto-incrementing primary key.
        scenario_name:   Human-readable scenario label.
        simulated_co2:   Aggregate simulated CO2 level in ppm.
        parameters:      JSON blob of scenario input parameters.
        sim_time:        UTC datetime when the simulation was run.
        baseline_co2:    Baseline CO2 before the scenario intervention.
        reduction_pct:   Percentage reduction vs baseline (can be negative).
        hourly_forecast: JSON array of hour-by-hour CO2 forecasts.
    """

    __tablename__ = "SimulationResults"

    sim_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    simulated_co2: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sim_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    baseline_co2: Mapped[float | None] = mapped_column(Float, nullable=True)
    reduction_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    hourly_forecast: Mapped[list | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the simulation result to a JSON-safe dictionary."""
        return {
            "sim_id": self.sim_id,
            "scenario_name": self.scenario_name,
            "simulated_co2": self.simulated_co2,
            "parameters": self.parameters,
            "sim_time": self.sim_time.isoformat() if self.sim_time else None,
            "baseline_co2": self.baseline_co2,
            "reduction_pct": self.reduction_pct,
            "hourly_forecast": self.hourly_forecast,
        }

    def __repr__(self) -> str:
        return (
            f"<SimulationResult id={self.sim_id} scenario={self.scenario_name!r} "
            f"co2={self.simulated_co2}>"
        )


# ---------------------------------------------------------------------------
# 6. Alert
# ---------------------------------------------------------------------------


class Alert(db.Model):
    """Threshold-breach notification record.

    Attributes:
        alert_id:   Auto-incrementing primary key.
        data_id:    Optional FK to the triggering :class:`EnvironmentalData` row.
        sensor_id:  Raw sensor identifier (denormalised for query convenience).
        alert_type: Category string e.g. ``'warning'`` or ``'critical'``.
        message:    Human-readable alert description.
        alert_time: UTC datetime the alert was raised.
        status:     Lifecycle status; defaults to ``'Active'``.
    """

    __tablename__ = "Alerts"

    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("EnvironmentalData.data_id", ondelete="SET NULL"),
        nullable=True,
    )
    sensor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alert_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active")

    # Relationship
    environmental_data: Mapped["EnvironmentalData | None"] = relationship(
        "EnvironmentalData", back_populates="alerts"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the alert to a JSON-safe dictionary."""
        return {
            "alert_id": self.alert_id,
            "data_id": self.data_id,
            "sensor_id": self.sensor_id,
            "alert_type": self.alert_type,
            "message": self.message,
            "alert_time": self.alert_time.isoformat() if self.alert_time else None,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.alert_id} type={self.alert_type!r} "
            f"sensor={self.sensor_id} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# 7. Threshold
# ---------------------------------------------------------------------------


class Threshold(db.Model):
    """Per-sensor configurable CO2 alert thresholds.

    Attributes:
        threshold_id:        Auto-incrementing primary key.
        sensor_id:           Unique sensor identifier this threshold applies to.
        warning_threshold:   CO2 ppm level that triggers a warning alert (default 450).
        critical_threshold:  CO2 ppm level that triggers a critical alert (default 500).
    """

    __tablename__ = "Thresholds"

    threshold_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # One threshold row per sensor - enforced at DB level via unique constraint.
    sensor_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    warning_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=450.0
    )
    critical_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=500.0
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the threshold to a JSON-safe dictionary."""
        return {
            "threshold_id": self.threshold_id,
            "sensor_id": self.sensor_id,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
        }

    def __repr__(self) -> str:
        return (
            f"<Threshold id={self.threshold_id} sensor={self.sensor_id} "
            f"warn={self.warning_threshold} crit={self.critical_threshold}>"
        )

