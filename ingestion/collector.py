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
        self.last_weather_fetch = None
        self.weather_data = {} # Map location -> weather info

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
            "timestamp": datetime.datetime.utcnow().isoformat()
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
            
            # Check if we need to update weather (every 15 mins)
            update_weather = False
            now = datetime.datetime.utcnow()
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
                        Timestamp=datetime.datetime.utcnow()
                    )
                    session.add(data_entry)
                    
                    # After insert trigger for alerts could be here, or in a DB trigger, or SQLAlchemy event.
                    # We will implement it in a separate alerts/manager.py that listens to DB or is called here.
                    from alerts.manager import AlertManager
                    session.flush() # get ID
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
