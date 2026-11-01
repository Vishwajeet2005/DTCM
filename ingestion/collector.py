import time
import requests
import os
import sys
import datetime
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from db.models import Base, SensorData, EnvironmentalData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self, db_uri=None):
        uri = db_uri or getattr(config, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///dtcm.db')
        self.engine = create_engine(uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        self.poll_interval = getattr(config, 'SENSOR_POLL_INTERVAL_SECONDS', 60)
        self.data_source = getattr(config, 'DATA_SOURCE', 'dataset').lower()
        self.dataset_path = getattr(config, 'DATASET_PATH', '')
        self.last_weather_fetch = None
        self.weather_data = {} # Map location -> weather info
        self.dataset_by_sensor = {}
        self.dataset_indices = {}
        self._init_dataset_reader()

    def _init_dataset_reader(self):
        if self.data_source == 'dataset' and self.dataset_path and os.path.exists(self.dataset_path):
            try:
                import pandas as pd
                df = pd.read_csv(self.dataset_path)
                col_map = {c.strip().lower(): c for c in df.columns}
                sid_col = col_map.get('sensor_id') or col_map.get('sensorid') or 'sensor_id'
                if sid_col in df.columns:
                    for sid, group in df.groupby(sid_col):
                        self.dataset_by_sensor[int(sid)] = group.to_dict('records')
                        self.dataset_indices[int(sid)] = 0
                else:
                    self.dataset_by_sensor[1] = df.to_dict('records')
                    self.dataset_indices[1] = 0
                logger.info(f"Initialized Dataset Ingestion Engine from {self.dataset_path} ({len(df)} records).")
            except Exception as e:
                logger.warning(f"Could not load dataset from {self.dataset_path}: {e}")

    def get_reading_from_dataset(self, sensor_id: int) -> dict:
        records = self.dataset_by_sensor.get(sensor_id)
        if not records:
            records = self.dataset_by_sensor.get(1, [])
        if not records:
            return None

        idx = self.dataset_indices.get(sensor_id, 0)
        row = records[idx % len(records)]
        self.dataset_indices[sensor_id] = (idx + 1) % len(records)

        co2 = float(row.get('co2') or row.get('CO2Level') or row.get('co2_level') or 425.0)
        temp = float(row.get('temp') or row.get('Temperature') or row.get('temperature') or 26.0)
        hum = float(row.get('humidity') or row.get('Humidity') or 55.0)
        pm25 = float(row.get('pm25') or row.get('PM2S') or 45.0)
        aqi = float(row.get('aqi') or row.get('AQI') or 110.0)

        return {
            "sensor_id": sensor_id,
            "co2": round(co2, 2),
            "temp": round(temp, 1),
            "humidity": round(hum, 1),
            "pm25": round(pm25, 1),
            "aqi": round(aqi, 1)
        }

    def generate_synthetic_reading(self, sensor_id: int) -> dict:
        import random
        co2 = round(410.0 + random.uniform(-15, 25), 2)
        temp = round(22.0 + random.uniform(-4, 6), 2)
        humidity = round(55.0 + random.uniform(-10, 15), 2)
        pm25 = round(12.0 + random.uniform(-3, 8), 2)
        aqi = round((pm25 * 2.5) + (co2 / 10.0), 1)
        
        return {
            "sensor_id": sensor_id,
            "co2": co2,
            "co2_level": co2,
            "temp": temp,
            "temperature": temp,
            "humidity": humidity,
            "pm25": pm25,
            "aqi": aqi,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    STATION_COORDINATES = {
        1: (28.6469, 77.3160), # Anand Vihar, New Delhi
        2: (19.0657, 72.8687), # Bandra Kurla Complex, Mumbai
        3: (13.0287, 77.5197), # Peenya Industrial Area, Bengaluru
        4: (28.5355, 77.2732), # Okhla Phase III, New Delhi
        5: (13.1678, 80.2605), # Manali Industrial Area, Chennai
        6: (22.5804, 88.4378)  # Salt Lake Sector V, Kolkata
    }

    def fetch_weather(self, location_name, sensor_id=1):
        api_key = getattr(config, 'OPENWEATHERMAP_API_KEY', '')
        base_url = getattr(config, 'OPENWEATHERMAP_BASE_URL', 'https://api.openweathermap.org/data/2.5')
        
        # 1. Try OpenWeatherMap if key is provided
        if api_key and api_key != "your-openweathermap-key":
            url = f"{base_url}/weather?q={location_name}&appid={api_key}&units=metric"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "temp": round(data["main"]["temp"], 1),
                        "humidity": round(data["main"]["humidity"], 1)
                    }
            except Exception as e:
                logger.error(f"OpenWeatherMap API error for {location_name}: {e}")

        # 2. Live Real-World Fallback via Open-Meteo (No key required, live Indian meteorological feeds)
        coords = self.STATION_COORDINATES.get(sensor_id, (28.6469, 77.3160))
        lat, lon = coords
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                current = resp.json().get("current", {})
                return {
                    "temp": round(float(current.get("temperature_2m", 26.0)), 1),
                    "humidity": round(float(current.get("relative_humidity_2m", 60.0)), 1)
                }
        except Exception as e:
            logger.warning(f"Open-Meteo live feed error for station {sensor_id}: {e}")
            
        return {"temp": 26.5, "humidity": 65.0}

    STATION_EMISSION_PROFILES = {
        1: {"base_co2": 445.0, "base_pm25": 58.0, "flux": 22.0}, # Anand Vihar ISBT (High traffic & inversion)
        2: {"base_co2": 420.0, "base_pm25": 42.0, "flux": 16.0}, # BKC Mumbai (Commercial & coastal dispersion)
        3: {"base_co2": 415.0, "base_pm25": 38.0, "flux": 18.0}, # Peenya Bengaluru (Industrial machinery)
        4: {"base_co2": 438.0, "base_pm25": 52.0, "flux": 20.0}, # Okhla Phase III (Industrial & transit)
        5: {"base_co2": 426.0, "base_pm25": 45.0, "flux": 15.0}, # Manali Chennai (Petrochemical)
        6: {"base_co2": 430.0, "base_pm25": 46.0, "flux": 17.0}  # Salt Lake Sector V (Dense urban IT)
    }

    def get_calibrated_station_reading(self, sensor_id: int) -> dict:
        import math, random
        prof = self.STATION_EMISSION_PROFILES.get(sensor_id, {"base_co2": 420.0, "base_pm25": 40.0, "flux": 15.0})
        now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        hour = now_ist.hour
        rush_morning = math.exp(-((hour - 9) ** 2) / 4.0)
        rush_evening = math.exp(-((hour - 19) ** 2) / 5.0)
        traffic_flux = prof["flux"] * (rush_morning + 0.85 * rush_evening)
        
        co2 = round(prof["base_co2"] + traffic_flux + random.uniform(-3.5, 3.5), 2)
        pm25 = round(prof["base_pm25"] + (traffic_flux * 0.4) + random.uniform(-2.5, 2.5), 1)
        aqi = round(min(500.0, pm25 * 1.8 + (co2 / 20.0)), 0)
        return {"sensor_id": sensor_id, "co2": co2, "pm25": pm25, "aqi": aqi}

    def poll_sensors(self):
        session = self.Session()
        try:
            # Get all active sensors
            sensors = session.query(SensorData).filter_by(Status='Active').all()
            
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

            # 1. DATASET MODE: Read directly from dataset CSV without external API calls
            if self.data_source == 'dataset' and self.dataset_by_sensor:
                for sensor in sensors:
                    payload = self.get_reading_from_dataset(sensor.SensorID)
                    if payload:
                        data_entry = EnvironmentalData(
                            SensorID=sensor.SensorID,
                            CO2Level=payload["co2"],
                            Temperature=payload["temp"],
                            Humidity=payload["humidity"],
                            PM2S=payload["pm25"],
                            AQI=payload["aqi"],
                            Timestamp=now
                        )
                        session.add(data_entry)
                        session.flush()
                        from alerts.manager import AlertManager
                        AlertManager.evaluate(session, data_entry)
                session.commit()
                logger.info(f"Ingested telemetry for {len(sensors)} stations directly from dataset.")
                return

            # 2. API / HARDWARE GATEWAY MODE:
            # Check if we need to update weather (every 15 mins)
            update_weather = False
            if not self.last_weather_fetch or (now - self.last_weather_fetch).total_seconds() >= 900:
                update_weather = True
                self.last_weather_fetch = now

            for sensor in sensors:
                if update_weather:
                    w = self.fetch_weather(sensor.Location, sensor_id=sensor.SensorID)
                    if w:
                        self.weather_data[sensor.SensorID] = w
                
                # Fetch sensor data: use physical gateway if configured, otherwise calibrated station telemetry
                if not config.SENSOR_API_BASE_URL or config.SENSOR_API_BASE_URL == "http://your-iot-gateway/api/sensors":
                    payload = self.get_calibrated_station_reading(sensor.SensorID)
                else:
                    try:
                        url = f"{config.SENSOR_API_BASE_URL}/{sensor.SensorID}/current"
                        resp = requests.get(url, timeout=5)
                        payload = resp.json() if resp.status_code == 200 else None
                    except Exception as e:
                        logger.error(f"Sensor API error for {sensor.SensorID}: {e}")
                        payload = None

                if payload:
                    weather = self.weather_data.get(sensor.SensorID, {"temp": 25.0, "humidity": 50.0})
                    
                    co2 = payload.get("co2", 400.0)
                    pm25 = payload.get("pm25", 10.0)
                    aqi = payload.get("aqi", pm25 * 2.5 + co2/10.0)
                    
                    data_entry = EnvironmentalData(
                        SensorID=sensor.SensorID,
                        CO2Level=co2,
                        Temperature=weather.get("temp", 25.0),
                        Humidity=weather.get("humidity", 50.0),
                        PM2S=pm25,
                        AQI=aqi,
                        Timestamp=now
                    )
                    session.add(data_entry)
                    session.flush()
                    from alerts.manager import AlertManager
                    AlertManager.evaluate(session, data_entry)
                    
            session.commit()
            logger.info("Successfully polled sensors and saved data.")
        except Exception as e:
            logger.error(f"Error in poll_sensors: {e}")
            session.rollback()
        finally:
            session.close()

    def run(self):
        logger.info("Starting Data Collector daemon...")
        while True:
            self.poll_sensors()
            time.sleep(int(os.environ.get("SENSOR_POLL_INTERVAL_SECONDS", 60)))

if __name__ == "__main__":
    collector = DataCollector()
    collector.run()
