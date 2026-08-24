"""
db/init_db.py - Database initialisation and seed-data script for DTCM.

Usage (standalone)::

    python -m db.init_db

Or import and call :func:`init_database` from within a running Flask context.

Steps performed
---------------
1. Create all SQLAlchemy tables (idempotent - safe to re-run).
2. Seed 5 default :class:`~db.models.SensorData` rows.
3. Seed a default :class:`~db.models.Threshold` row for each sensor.
4. Create a default *administrator* :class:`~db.models.User`.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that ``from app import ...`` works
# when the script is executed directly (python db/init_db.py).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app import create_app  # noqa: E402  (import after path manipulation)
from db.models import db, SensorData, Threshold, User  # noqa: E402


# ---------------------------------------------------------------------------
# Seed constants
# ---------------------------------------------------------------------------

_DEFAULT_SENSOR_LOCATIONS: list[str] = [
    "Connaught Place, New Delhi",
    "Bandra Kurla Complex, Mumbai",
    "Electronic City, Bengaluru",
    "T. Nagar, Chennai",
    "Salt Lake Sector V, Kolkata",
]

_DEFAULT_SENSOR_TYPE: str = "NDIR CO2 Sensor"

_ADMIN_EMAIL: str = "admin@dtcm.local"
_ADMIN_PASSWORD: str = "Admin@1234"
_ADMIN_NAME: str = "System Admin"
_ADMIN_ROLE: str = "administrator"


# ---------------------------------------------------------------------------
# Main initialisation function
# ---------------------------------------------------------------------------


def init_database(config_name: str = "development") -> None:
    """Initialise the database: create tables and insert seed data.

    This function is idempotent - running it multiple times will not create
    duplicate rows for the default sensors or the admin user.

    Args:
        config_name: The configuration environment to boot Flask with.
                     Valid values: ``'development'``, ``'production'``,
                     ``'testing'``, ``'default'``.
    """
    app = create_app(config_name)

    with app.app_context():
        # ----------------------------------------------------------------
        # Step 1: Create tables
        # ----------------------------------------------------------------
        print("[init_db] Creating database tables...")
        db.create_all()
        print("[init_db] ? Tables created (or already exist).")

        # ----------------------------------------------------------------
        # Step 2: Seed default sensors
        # ----------------------------------------------------------------
        print("[init_db] Seeding default sensors...")
        seeded_sensors: list[SensorData] = []

        for location in _DEFAULT_SENSOR_LOCATIONS:
            existing = SensorData.query.filter_by(location=location).first()
            if existing:
                print(f"[init_db]   - Sensor '{location}' already exists - skipping.")
                seeded_sensors.append(existing)
            else:
                sensor = SensorData(
                    location=location,
                    type=_DEFAULT_SENSOR_TYPE,
                    installation_date=datetime.date.today(),
                    status="Active",
                )
                db.session.add(sensor)
                # Flush to get the auto-assigned sensor_id before commit.
                db.session.flush()
                seeded_sensors.append(sensor)
                print(f"[init_db]   + Sensor '{location}' created (id={sensor.sensor_id}).")

        db.session.commit()
        print("[init_db] ? Sensor seeding complete.")

        # ----------------------------------------------------------------
        # Step 3: Seed default thresholds for each sensor
        # ----------------------------------------------------------------
        print("[init_db] Seeding default thresholds...")

        for sensor in seeded_sensors:
            existing_thresh = Threshold.query.filter_by(
                sensor_id=sensor.sensor_id
            ).first()
            if existing_thresh:
                print(
                    f"[init_db]   - Threshold for sensor {sensor.sensor_id} "
                    f"already exists - skipping."
                )
            else:
                threshold = Threshold(
                    sensor_id=sensor.sensor_id,
                    warning_threshold=450.0,
                    critical_threshold=500.0,
                )
                db.session.add(threshold)
                print(
                    f"[init_db]   + Threshold created for sensor {sensor.sensor_id} "
                    f"(warn=450 ppm, crit=500 ppm)."
                )

        db.session.commit()
        print("[init_db] ? Threshold seeding complete.")

        # ----------------------------------------------------------------
        # Step 4: Create default admin user
        # ----------------------------------------------------------------
        print("[init_db] Seeding default admin user...")

        existing_admin = User.query.filter_by(email=_ADMIN_EMAIL).first()
        if existing_admin:
            print(
                f"[init_db]   - Admin user '{_ADMIN_EMAIL}' already exists - skipping."
            )
        else:
            admin = User(
                name=_ADMIN_NAME,
                email=_ADMIN_EMAIL,
                role=_ADMIN_ROLE,
            )
            admin.set_password(_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(
                f"[init_db]   + Admin user '{_ADMIN_EMAIL}' created "
                f"(id={admin.user_id})."
            )

        print("[init_db] ? Admin user seeding complete.")
        print("[init_db] ========== Database initialisation finished ==========")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow passing a config name as the first CLI argument, e.g.:
    #   python -m db.init_db production
    cfg = sys.argv[1] if len(sys.argv) > 1 else "development"
    init_database(config_name=cfg)



