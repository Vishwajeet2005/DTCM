"""
generate_synthetic_data.py
==========================
Standalone script that populates the DTCM SQLite database with 50,000 rows of
realistic CO2 sensor readings spanning two years.

Run directly:
    python scripts/generate_synthetic_data.py

The script uses SQLAlchemy engine/session directly (no Flask app context needed).
"""

import sys
import os
import math
import random
import logging
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so db.models can be imported.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from db.models import SensorData, EnvironmentalData  # noqa: E402  (after path fix)

# ---------------------------------------------------------------------------
# Attempt to pull DATABASE_URL from config; fall back to default SQLite path.
# ---------------------------------------------------------------------------
try:
    from config import Config  # type: ignore
    DATABASE_URL = Config.SQLALCHEMY_DATABASE_URI
except Exception:
    DATABASE_URL = f"sqlite:///instance/dtcm.db"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SENSOR_COUNT = 5
SENSOR_NAMES = [
    "Connaught Place, New Delhi",
    "Bandra Kurla Complex, Mumbai",
    "Electronic City, Bengaluru",
    "T. Nagar, Chennai",
    "Salt Lake Sector V, Kolkata",
]
# Fixed ppm offset per sensor (index = sensor_id - 1)
SENSOR_OFFSETS = [0, 40, -10, -20, 25]

# CO2 generation parameters
CO2_BASE = 415.0          # ppm
CO2_SEASONAL_AMP = 20.0   # ppm
CO2_PEAK_AMP = 30.0       # ppm
CO2_NOISE_STD = 5.0
CO2_MIN, CO2_MAX = 380.0, 580.0

# Temperature parameters
TEMP_BASE = 22.0
TEMP_SEASONAL_AMP = 15.0
TEMP_DAILY_AMP = 3.0
TEMP_NOISE_STD = 1.0

# Humidity parameters
HUM_BASE = 60.0
HUM_SEASONAL_AMP = 20.0
HUM_NOISE_STD = 5.0
HUM_MIN, HUM_MAX = 20.0, 95.0

# PM2.5 parameters
PM25_MIN, PM25_MAX = 5.0, 150.0

# AQI weights
AQI_MIN, AQI_MAX = 0.0, 500.0

PROGRESS_INTERVAL = 5000  # print progress every N rows


def _gaussian(x: float, center: float, sigma: float = 1.5) -> float:
    """Return Gaussian bump value centred at *center* with given *sigma*."""
    return math.exp(-0.5 * ((x - center) / sigma) ** 2)


def generate_co2(
    timestamp: datetime, day_of_year: int, hour: float, sensor_idx: int
) -> float:
    """
    Compute a realistic CO2 reading (ppm) for *sensor_idx* at *timestamp*.

    Parameters
    ----------
    timestamp:   datetime of the reading (unused directly; kept for clarity).
    day_of_year: 1-based day index used for seasonal cosine.
    hour:        fractional hour of day (0-23).
    sensor_idx:  0-based sensor index.
    """
    # Seasonal variation: higher in winter (day_of_year ~ 1 / 365 = winter)
    # cos(2*pi * day_of_year / 365) peaks at day 0 (Jan 1).
    seasonal = CO2_SEASONAL_AMP * math.cos(2 * math.pi * day_of_year / 365.0)

    # Daily rush-hour peaks: morning (8 AM) and evening (18 PM)
    morning_peak = CO2_PEAK_AMP * _gaussian(hour, 8.0)
    evening_peak = CO2_PEAK_AMP * _gaussian(hour, 18.0)

    # Sensor-specific fixed offset
    offset = SENSOR_OFFSETS[sensor_idx]

    # Gaussian noise
    noise = random.gauss(0, CO2_NOISE_STD)

    co2 = CO2_BASE + seasonal + morning_peak + evening_peak + offset + noise
    return max(CO2_MIN, min(CO2_MAX, co2))


def generate_temperature(day_of_year: int, hour: float) -> float:
    """Return realistic temperature (-C)."""
    seasonal = TEMP_SEASONAL_AMP * math.cos(2 * math.pi * day_of_year / 365.0)
    daily = TEMP_DAILY_AMP * math.sin(2 * math.pi * (hour - 6) / 24.0)
    noise = random.gauss(0, TEMP_NOISE_STD)
    return round(TEMP_BASE - seasonal + daily + noise, 2)


def generate_humidity(day_of_year: int) -> float:
    """Return realistic relative humidity (%)."""
    # Humidity inversely correlated with temperature season
    seasonal = HUM_SEASONAL_AMP * math.cos(2 * math.pi * day_of_year / 365.0)
    noise = random.gauss(0, HUM_NOISE_STD)
    hum = HUM_BASE + seasonal + noise
    return round(max(HUM_MIN, min(HUM_MAX, hum)), 2)


def generate_pm25(co2: float) -> float:
    """Return PM2.5 (-g/m-) correlated with excess CO2 above baseline."""
    co2_excess = max(0.0, co2 - CO2_BASE)
    pm25 = 0.3 * co2_excess + random.gauss(15, 8)
    return round(max(PM25_MIN, min(PM25_MAX, pm25)), 2)


def compute_aqi(co2: float, pm25: float) -> float:
    """Simplified AQI from CO2 and PM2.5."""
    aqi = 0.05 * co2 + 0.5 * pm25
    return round(max(AQI_MIN, min(AQI_MAX, aqi)), 2)


def build_engine_and_session():
    """
    Create SQLAlchemy engine and sessionmaker.

    Ensures all tables exist via metadata.create_all().
    """
    engine = create_engine(DATABASE_URL, echo=False)

    # Import Base lazily to avoid circular imports
    
    

    Session = sessionmaker(bind=engine)
    return engine, Session


def main() -> None:
    """Entry-point: generate and insert 50,000 rows of CO2 sensor data."""
    random.seed(42)  # reproducible output

    engine, Session = build_engine_and_session()
    session = Session()

    # Calculate date range: exactly 2 years back from now
    end_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=2 * 365)

    # Pre-build hourly timestamp list
    total_hours = int((end_dt - start_dt).total_seconds() // 3600)
    logger.info(
        "Generating data: %d sensors - %d hours = %d rows",
        SENSOR_COUNT,
        total_hours,
        SENSOR_COUNT * total_hours,
    )

    inserted = 0
    batch: list[EnvironmentalData] = []
    BATCH_SIZE = 500  # flush to DB every 500 rows for memory efficiency

    for sensor_idx in range(SENSOR_COUNT):
        sensor_id = sensor_idx + 1
        current = start_dt

        while current < end_dt:
            day_of_year = current.timetuple().tm_yday
            hour = current.hour  # integer hour (0-23)

            co2 = generate_co2(current, day_of_year, float(hour), sensor_idx)
            temp = generate_temperature(day_of_year, float(hour))
            humidity = generate_humidity(day_of_year)
            pm25 = generate_pm25(co2)
            aqi = compute_aqi(co2, pm25)

            row = EnvironmentalData(
                sensor_id=sensor_id,
                timestamp=current.replace(tzinfo=None),  # store naive UTC
                co2_level=round(co2, 2),
                temperature=temp,
                humidity=humidity,
                pm25=round(pm25, 2),
                aqi=aqi,

                data_gap=False,
            )
            batch.append(row)
            inserted += 1

            # Flush batch
            if len(batch) >= BATCH_SIZE:
                session.bulk_save_objects(batch)
                session.commit()
                batch.clear()

            # Progress reporting
            if inserted % PROGRESS_INTERVAL == 0:
                print(f"  [Progress] Inserted {inserted:,} rows -", flush=True)

            current += timedelta(hours=1)

    # Flush any remaining rows
    if batch:
        session.bulk_save_objects(batch)
        session.commit()
        batch.clear()

    session.close()
    engine.dispose()

    print(f"\n? Done. Total rows inserted: {inserted:,}")
    logger.info("Synthetic data generation complete. Rows inserted: %d", inserted)


if __name__ == "__main__":
    main()


