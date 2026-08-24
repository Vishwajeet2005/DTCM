"""
collector.py
============
DataCollector class for the DTCM project.

Handles:
* Polling real IoT sensors via HTTP (with synthetic fallback).
* Fetching weather data from OpenWeatherMap.
* Inserting validated readings into EnvironmentalData table.
* Running a background polling loop in a daemon thread.
"""

import logging
import math
import os
import random
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sensor metadata
# ---------------------------------------------------------------------------
SENSOR_LOCATIONS: dict[int, tuple[str, float, float]] = {
    1: ("Downtown Core",         40.7128, -74.0060),
    2: ("Industrial Zone North", 40.7282, -74.0776),
    3: ("Residential East",      40.7489, -73.9680),
    4: ("Green Park West",       40.7812, -73.9665),
    5: ("Traffic Hub Central",   40.7023, -73.9871),
}

# Fixed ppm offsets matching generate_synthetic_data.py
SENSOR_OFFSETS: dict[int, float] = {1: 0, 2: 40, 3: -10, 4: -20, 5: 25}

# CO2 generation constants (mirrors generate_synthetic_data.py)
CO2_BASE        = 415.0
CO2_SEASONAL    = 20.0
CO2_PEAK_AMP    = 30.0
CO2_NOISE_STD   = 5.0
CO2_MIN, CO2_MAX = 380.0, 580.0

TEMP_BASE, TEMP_SEASONAL, TEMP_DAILY, TEMP_NOISE = 22.0, 15.0, 3.0, 1.0
HUM_BASE, HUM_SEASONAL, HUM_NOISE = 60.0, 20.0, 5.0
HUM_MIN, HUM_MAX = 20.0, 95.0
PM25_MIN, PM25_MAX = 5.0, 150.0
AQI_MIN, AQI_MAX = 0.0, 500.0

OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def _gaussian(x: float, center: float, sigma: float = 1.5) -> float:
    """Gaussian bump centred at *center*."""
    return math.exp(-0.5 * ((x - center) / sigma) ** 2)


class DataCollector:
    """
    Collects CO2 and environmental readings from IoT sensors and weather APIs.

    Parameters
    ----------
    app : Optional Flask application instance. When provided, the collector
          uses app.config to obtain runtime settings.
    """

    def __init__(self, app=None) -> None:
        self.app = app
        self._owm_warning_logged = False  # log missing API key only once
        self._running = False

        # Read config values (with safe defaults for standalone use)
        if app is not None:
            self.sensor_api_base = app.config.get("SENSOR_API_BASE_URL", "")
            self.poll_interval   = int(app.config.get("SENSOR_POLL_INTERVAL_SECONDS", 60))
            self.owm_api_key     = app.config.get("OPENWEATHERMAP_API_KEY", "")
            self.api_timeout     = int(app.config.get("SENSOR_API_TIMEOUT_SECONDS", 5))
        else:
            self.sensor_api_base = os.getenv("SENSOR_API_BASE_URL", "")
            self.poll_interval   = int(os.getenv("SENSOR_POLL_INTERVAL_SECONDS", "60"))
            self.owm_api_key     = os.getenv("OPENWEATHERMAP_API_KEY", "")
            self.api_timeout     = int(os.getenv("SENSOR_API_TIMEOUT_SECONDS", "5"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def poll_iot_sensors(self) -> list[dict]:
        """
        Attempt to fetch readings from the real IoT sensor REST API.

        On connection failure, timeout, or missing base URL, a synthetic
        reading is generated for each sensor as a fallback.

        Returns
        -------
        List of reading dicts (one per sensor).
        """
        readings: list[dict] = []

        for sensor_id in SENSOR_LOCATIONS:
            reading = self._fetch_sensor_reading(sensor_id)
            readings.append(reading)

        return readings

    def fetch_weather_data(self, lat: float, lon: float) -> Optional[dict]:
        """
        Fetch current weather from OpenWeatherMap for the given coordinates.

        Parameters
        ----------
        lat : Latitude.
        lon : Longitude.

        Returns
        -------
        Dict with keys temperature, humidity, wind_speed, or None on error.
        """
        if not self.owm_api_key:
            if not self._owm_warning_logged:
                logger.info(
                    "OPENWEATHERMAP_API_KEY not set - weather fetch disabled."
                )
                self._owm_warning_logged = True
            return None

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.owm_api_key,
            "units": "metric",
        }
        try:
            resp = requests.get(OWM_BASE_URL, params=params, timeout=self.api_timeout)
            resp.raise_for_status()
            data = resp.json()
            return {
                "temperature": data["main"]["temp"],
                "humidity":    data["main"]["humidity"],
                "wind_speed":  data["wind"]["speed"],
            }
        except RequestException as exc:
            logger.warning("Weather fetch failed for (%.4f, %.4f): %s", lat, lon, exc)
            return None

    def insert_reading(self, reading: dict, session) -> "EnvironmentalData":
        """
        Validate and persist a single sensor reading to EnvironmentalData.

        Also triggers AlertManager evaluation if available.

        Parameters
        ----------
        reading : Dict with sensor_id, timestamp, co2_level, etc.
        session : Active SQLAlchemy session.

        Returns
        -------
        The newly created EnvironmentalData ORM instance.
        """
        from db.models import EnvironmentalData  # type: ignore

        # Coerce numeric types with safe defaults
        sensor_id  = int(reading.get("sensor_id", 0))
        co2        = float(reading.get("co2_level", CO2_BASE))
        temp       = float(reading.get("temperature", TEMP_BASE))
        humidity   = float(reading.get("humidity", HUM_BASE))
        pm25       = float(reading.get("pm25", 10.0))
        aqi        = float(reading.get("aqi", 0.05 * co2 + 0.5 * pm25))
        data_gap   = bool(reading.get("data_gap", False))
        quality    = "gap" if data_gap else "good"
        ts         = reading.get("timestamp", datetime.now(timezone.utc).replace(tzinfo=None))

        row = EnvironmentalData(
            sensor_id=sensor_id,
            timestamp=ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts)),
            co2_level=round(co2, 2),
            temperature=round(temp, 2),
            humidity=round(humidity, 2),
            pm25=round(pm25, 2),
            aqi=round(aqi, 2),
            data_quality=quality,
            data_gap=data_gap,
        )
        session.add(row)
        session.commit()

        # Attempt to trigger alert evaluation (AlertManager may not be wired yet)
        try:
            from alerts.alert_manager import AlertManager  # type: ignore
            AlertManager().evaluate(row, session)
        except ImportError:
            pass  # AlertManager not yet available - silently skip
        except Exception as exc:
            logger.warning("AlertManager.evaluate failed: %s", exc)

        logger.debug(
            "Inserted reading: sensor_id=%d co2=%.2f ts=%s",
            sensor_id, co2, row.timestamp,
        )
        return row

    def generate_synthetic_reading(self, sensor_id: int) -> dict:
        """
        Generate a single realistic sensor reading for *sensor_id* at current time.

        Uses the same generation logic as generate_synthetic_data.py so that
        synthetic fallback readings are statistically consistent with the
        training data.

        Parameters
        ----------
        sensor_id : Integer sensor ID (1-5).

        Returns
        -------
        Dict ready to pass to insert_reading().
        """
        now = datetime.now(timezone.utc)
        day_of_year = now.timetuple().tm_yday
        hour = float(now.hour)

        # CO2
        seasonal = CO2_SEASONAL * math.cos(2 * math.pi * day_of_year / 365.0)
        morning_peak = CO2_PEAK_AMP * _gaussian(hour, 8.0)
        evening_peak = CO2_PEAK_AMP * _gaussian(hour, 18.0)
        offset = SENSOR_OFFSETS.get(sensor_id, 0)
        noise = random.gauss(0, CO2_NOISE_STD)
        co2 = max(CO2_MIN, min(CO2_MAX, CO2_BASE + seasonal + morning_peak + evening_peak + offset + noise))

        # Temperature
        seasonal_t = TEMP_SEASONAL * math.cos(2 * math.pi * day_of_year / 365.0)
        daily_t = TEMP_DAILY * math.sin(2 * math.pi * (hour - 6) / 24.0)
        temp = round(TEMP_BASE - seasonal_t + daily_t + random.gauss(0, TEMP_NOISE), 2)

        # Humidity
        seasonal_h = HUM_SEASONAL * math.cos(2 * math.pi * day_of_year / 365.0)
        humidity = round(max(HUM_MIN, min(HUM_MAX, HUM_BASE + seasonal_h + random.gauss(0, HUM_NOISE))), 2)

        # PM2.5 and AQI
        pm25 = round(max(PM25_MIN, min(PM25_MAX, 0.3 * max(0, co2 - CO2_BASE) + random.gauss(15, 8))), 2)
        aqi  = round(max(AQI_MIN, min(AQI_MAX, 0.05 * co2 + 0.5 * pm25)), 2)

        return {
            "sensor_id":   sensor_id,
            "timestamp":   now.replace(tzinfo=None),
            "co2_level":   round(co2, 2),
            "temperature": temp,
            "humidity":    humidity,
            "pm25":        pm25,
            "aqi":         aqi,
            "data_gap":    False,
        }

    def run_poll_loop(self) -> None:
        """
        Infinite polling loop executed in a background daemon thread.

        Every SENSOR_POLL_INTERVAL_SECONDS seconds, fetches readings from all
        sensors and inserts them into the database. Requires the Flask app
        to have been set so an application context can be pushed for DB access.
        """
        from sqlalchemy.orm import sessionmaker  # type: ignore

        logger.info(
            "DataCollector: poll loop starting (interval=%ds).", self.poll_interval
        )
        self._running = True

        while self._running:
            try:
                if self.app is not None:
                    # Use Flask-SQLAlchemy session inside app context
                    with self.app.app_context():
                        from db.models import db  # type: ignore
                        readings = self.poll_iot_sensors()
                        for reading in readings:
                            self.insert_reading(reading, db.session)
                else:
                    logger.warning(
                        "run_poll_loop: no Flask app provided - skipping insert."
                    )
            except Exception as exc:
                logger.error("Poll loop iteration failed: %s", exc, exc_info=True)

            time.sleep(self.poll_interval)

    def start_background_polling(self, app) -> None:
        """
        Launch run_poll_loop in a daemon thread.

        Parameters
        ----------
        app : Flask application instance.
        """
        self.app = app
        thread = threading.Thread(
            target=self.run_poll_loop,
            name="dtcm-sensor-poll",
            daemon=True,
        )
        thread.start()
        logger.info("DataCollector: background polling thread started.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_sensor_reading(self, sensor_id: int) -> dict:
        """
        Try real API, fall back to synthetic on any error.

        Parameters
        ----------
        sensor_id : 1-based sensor identifier.

        Returns
        -------
        Reading dict.
        """
        if not self.sensor_api_base:
            # No API base configured - use synthetic directly
            return self.generate_synthetic_reading(sensor_id)

        url = f"{self.sensor_api_base.rstrip('/')}/readings"
        params = {"sensor_id": sensor_id}

        try:
            resp = requests.get(url, params=params, timeout=self.api_timeout)
            resp.raise_for_status()
            data = resp.json()

            # Enrich with weather if coordinates available
            _, lat, lon = SENSOR_LOCATIONS.get(sensor_id, ("", 0.0, 0.0))
            if lat and lon:
                weather = self.fetch_weather_data(lat, lon)
                if weather:
                    data.setdefault("temperature", weather["temperature"])
                    data.setdefault("humidity",    weather["humidity"])

            data["sensor_id"] = sensor_id
            data["data_gap"]  = False
            return data

        except RequestException as exc:
            logger.warning(
                "Sensor API call failed for sensor_id=%d: %s. "
                "Using synthetic fallback.",
                sensor_id,
                exc,
            )
            reading = self.generate_synthetic_reading(sensor_id)
            reading["data_gap"] = True  # flag that real data was unavailable
            return reading

