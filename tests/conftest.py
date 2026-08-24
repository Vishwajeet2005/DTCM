"""
tests/conftest.py --- Digital Twin CO--- Monitor (DTCM)
====================================================
Shared pytest fixtures for the entire test suite.

Fixture hierarchy
-----------------
app               --- Flask application wired to TestingConfig (in-memory SQLite).
client            --- Flask test client derived from the ``app`` fixture.
db_session        --- SQLAlchemy session scoped to the test function.
sample_sensor     --- A single SensorData row committed to the test DB.
sample_data       --- 100 hourly EnvironmentalData rows for sensor 1.
auth_headers      --- JWT Bearer headers for an administrator user.
researcher_headers--- JWT Bearer headers for a researcher user.
general_headers   --- JWT Bearer headers for a general (unprivileged) user.
"""

from __future__ import annotations

import datetime
import json
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# App import --- app factory lives at project root as app.py
# ---------------------------------------------------------------------------
from app import create_app  # type: ignore[import]
from config import TestingConfig
from db.models import db as _db, EnvironmentalData, SensorData


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def app() -> Generator[Flask, None, None]:
    """Create a Flask app instance bound to TestingConfig (in-memory SQLite).

    All DB tables are created before the test runs and dropped afterwards to
    guarantee complete isolation between tests.

    Yields:
        A fully initialised :class:`flask.Flask` application.
    """
    flask_app = create_app(TestingConfig)

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app: Flask) -> FlaskClient:
    """Return a Flask test client for the given app fixture.

    Args:
        app: The pytest ``app`` fixture.

    Returns:
        A :class:`flask.testing.FlaskClient` instance.
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app: Flask) -> Generator[Session, None, None]:
    """Yield an active SQLAlchemy session for the current test.

    The session operates on the same in-memory SQLite database as the
    Flask test client so ORM changes are immediately visible to HTTP calls
    within the same test.

    Args:
        app: The pytest ``app`` fixture (provides the application context).

    Yields:
        An open :class:`sqlalchemy.orm.Session`.
    """
    with app.app_context():
        session: Session = _db.session
        yield session
        # Roll back uncommitted changes so the next fixture starts clean.
        session.rollback()


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def sample_sensor(db_session: Session) -> SensorData:
    """Create and persist a single SensorData row.

    Args:
        db_session: The active test DB session.

    Returns:
        The committed :class:`~db.models.SensorData` instance with a
        database-assigned ``sensor_id``.
    """
    sensor = SensorData(
        location="Test Zone A",
        type="NDIR",
        installation_date=datetime.date(2024, 1, 1),
        status="Active",
    )
    db_session.add(sensor)
    db_session.commit()
    db_session.refresh(sensor)
    return sensor


@pytest.fixture(scope="function")
def sample_data(db_session: Session, sample_sensor: SensorData) -> list[EnvironmentalData]:
    """Create 100 hourly EnvironmentalData rows attached to *sample_sensor*.

    Rows span the most-recent 100 hours with pseudo-random but realistic CO---
    (400---470 ppm), temperature (18---28 --C), humidity (40---70 %) and PM2.5
    (5---20 --g/m--) values. The random seed is fixed at 42 for reproducibility.

    Args:
        db_session: The active test DB session.
        sample_sensor: The sensor fixture to attach readings to.

    Returns:
        A list of 100 committed :class:`~db.models.EnvironmentalData` rows
        ordered by ascending timestamp.
    """
    import random

    random.seed(42)
    now = datetime.datetime.utcnow()
    rows: list[EnvironmentalData] = []

    for i in range(100):
        ts = now - datetime.timedelta(hours=100 - i)
        row = EnvironmentalData(
            sensor_id=sample_sensor.sensor_id,
            co2_level=round(400 + random.uniform(0, 70), 2),
            temperature=round(18 + random.uniform(0, 10), 2),
            humidity=round(40 + random.uniform(0, 30), 2),
            pm25=round(5 + random.uniform(0, 15), 2),
            aqi=round(50 + random.uniform(0, 50), 2),
            timestamp=ts,
            data_gap=False,
        )
        rows.append(row)

    db_session.bulk_save_objects(rows)
    db_session.commit()

    # Re-query so all instances have database-assigned PKs.
    return (
        db_session.query(EnvironmentalData)
        .filter_by(sensor_id=sample_sensor.sensor_id)
        .order_by(EnvironmentalData.timestamp)
        .all()
    )


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------


def _create_user_and_login(client: FlaskClient, name: str, email: str, role: str) -> dict:
    """Register a user via the API then log in to obtain a JWT Bearer token.

    Args:
        client: The Flask test client.
        name: User display name.
        email: Unique e-mail address used for both registration and login.
        role: One of the four valid DTCM RBAC roles.

    Returns:
        A headers dict with ``Authorization`` (Bearer token) and
        ``Content-Type`` keys, ready to be passed to ``client.<method>()``.
    """
    # 1. Register --- ignore the response; may already exist in edge cases.
    client.post(
        "/api/auth/register",
        data=json.dumps(
            {"name": name, "email": email, "password": "Test@1234", "role": role}
        ),
        content_type="application/json",
    )

    # 2. Login and extract the access token.
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({"email": email, "password": "Test@1234"}),
        content_type="application/json",
    )
    body = json.loads(resp.data)
    token: str = body.get("access_token", "")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="function")
def auth_headers(client: FlaskClient) -> dict:
    """Provide JWT Bearer headers authenticated as an **administrator**.

    Registers and logs in ``admin@dtcm.test`` with role=administrator.

    Args:
        client: The pytest ``client`` fixture.

    Returns:
        Dict with ``Authorization`` and ``Content-Type`` headers.
    """
    return _create_user_and_login(
        client,
        name="Test Admin",
        email="admin@dtcm.test",
        role="administrator",
    )


@pytest.fixture(scope="function")
def researcher_headers(client: FlaskClient) -> dict:
    """Provide JWT Bearer headers authenticated as a **researcher**.

    Registers and logs in ``researcher@dtcm.test`` with role=researcher.

    Args:
        client: The pytest ``client`` fixture.

    Returns:
        Dict with ``Authorization`` and ``Content-Type`` headers.
    """
    return _create_user_and_login(
        client,
        name="Test Researcher",
        email="researcher@dtcm.test",
        role="researcher",
    )


@pytest.fixture(scope="function")
def general_headers(client: FlaskClient) -> dict:
    """Provide JWT Bearer headers authenticated as a **general** user.

    General users have the lowest privilege level.  Registers and logs in
    ``general@dtcm.test`` with role=general.

    Args:
        client: The pytest ``client`` fixture.

    Returns:
        Dict with ``Authorization`` and ``Content-Type`` headers.
    """
    return _create_user_and_login(
        client,
        name="Test General",
        email="general@dtcm.test",
        role="general",
    )

