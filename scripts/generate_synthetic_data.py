import os
import sys
import datetime
import math
import random
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.models import Base, SensorData, EnvironmentalData, Users
import bcrypt

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///dtcm.db")

def generate_indian_sensor_data():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Clear old data
    session.query(EnvironmentalData).delete()
    session.query(SensorData).delete()
    session.commit()

    # Real-world Indian Urban & Industrial Monitoring Stations
    sensors_meta = [
        {"name": "Anand Vihar ISBT, New Delhi", "type": "NDIR CO2 & CPCB AQI", "lat": 28.6469, "lon": 77.3160, "base_co2": 485.0, "temp_offset": 0.0},
        {"name": "Bandra-Kurla Complex (BKC), Mumbai", "type": "Optical CO2 & MPCB Telemetry", "lat": 19.0657, "lon": 72.8687, "base_co2": 445.0, "temp_offset": 3.0},
        {"name": "Peenya Industrial Area, Bengaluru", "type": "Electrochemical & KSPCB Monitor", "lat": 13.0287, "lon": 77.5197, "base_co2": 460.0, "temp_offset": -2.0},
        {"name": "Okhla Industrial Area Phase-III, New Delhi", "type": "NDIR Industrial Sensor", "lat": 28.5355, "lon": 77.2732, "base_co2": 510.0, "temp_offset": 0.5},
        {"name": "Manali Petrochemical Corridor, Chennai", "type": "Infrared Gas Sensor", "lat": 13.1652, "lon": 80.2612, "base_co2": 475.0, "temp_offset": 4.0},
        {"name": "Sector V, Salt Lake, Kolkata", "type": "Laser Particle & CO2 Sensor", "lat": 22.5735, "lon": 88.4331, "base_co2": 450.0, "temp_offset": 2.0}
    ]

    sensor_objs = []
    for s in sensors_meta:
        obj = SensorData(
            Location=s["name"],
            Type=s["type"],
            InstallationDate=datetime.datetime(2023, 1, 1),
            Status="Active"
        )
        session.add(obj)
        sensor_objs.append((obj, s))
    
    session.commit()

    # Ensure admin users exist
    seed_users = [
        ('Admin Official', 'admin@dtcm.com', 'administrator', 'admin123'),
        ('CPCB Authority Lead', 'authority@dtcm.com', 'environmental_authority', 'authority123'),
        ('IIT Research Scientist', 'researcher@dtcm.com', 'researcher', 'researcher123'),
        ('Resident Citizen', 'citizen@dtcm.com', 'general', 'citizen123'),
    ]
    for name, email, role, pwd in seed_users:
        if not session.query(Users).filter_by(Email=email).first():
            hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
            session.add(Users(Email=email, PasswordHash=hashed, Role=role, Name=name))
    session.commit()

    # Generate 1 year of hourly historical readings
    start_date = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=365)
    end_date = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    current_time = start_date
    batch_data = []
    print(f"Generating real-world Indian telemetry for {len(sensor_objs)} monitoring stations over 1 year...")

    while current_time <= end_date:
        hour = current_time.hour
        day_of_year = current_time.timetuple().tm_yday
        month = current_time.month

        # North Indian winter inversion (Nov to Feb) increases CO2 & PM2.5
        winter_inversion = 35.0 if month in [11, 12, 1, 2] else 0.0

        for sensor_obj, meta in sensor_objs:
            base = meta["base_co2"]
            
            # Diurnal traffic surges (Indian rush hours: 8:30 - 11:00 AM, 6:00 - 9:00 PM)
            traffic_flux = 0.0
            if 8 <= hour <= 11:
                traffic_flux = 35.0 * math.sin(math.pi * (hour - 8) / 3)
            elif 18 <= hour <= 21:
                traffic_flux = 40.0 * math.sin(math.pi * (hour - 18) / 3)
            else:
                traffic_flux = -12.0 + random.uniform(-4, 4)

            co2 = base + traffic_flux + (winter_inversion if 'Delhi' in meta['name'] or 'Kolkata' in meta['name'] else 5.0) + random.uniform(-8, 8)
            co2 = max(390.0, min(650.0, co2))

            # Indian temperatures: 15C (winter north) to 42C (summer)
            base_temp = 28.0 + meta["temp_offset"]
            temp_seasonal = 8.0 * math.sin(2 * math.pi * (day_of_year - 110) / 365.25)
            temp_diurnal = 5.0 * math.sin(math.pi * (hour - 6) / 12)
            temp = round(base_temp + temp_seasonal + temp_diurnal + random.uniform(-1, 1), 1)

            # Humidity: High during monsoon (July-Sept)
            monsoon_hum = 25.0 if month in [6, 7, 8, 9] else 0.0
            humidity = round(max(25.0, min(95.0, 50.0 + monsoon_hum + 15.0 * math.cos(2 * math.pi * hour / 24) + random.uniform(-5, 5))), 1)

            # PM2.5 in Indian metro centers (40 - 240 ug/m3)
            pm25 = round(max(25.0, min(350.0, (co2 - 400.0) * 0.45 + (winter_inversion * 1.5) + random.uniform(10, 30))), 1)

            # Indian National AQI formulation approximation
            aqi = round(min(500.0, pm25 * 1.8 + random.uniform(5, 20)), 0)

            data = EnvironmentalData(
                SensorID=sensor_obj.SensorID,
                CO2Level=round(co2, 2),
                Temperature=temp,
                Humidity=humidity,
                PM2S=pm25,
                AQI=aqi,
                Timestamp=current_time,
                data_gap=False
            )
            batch_data.append(data)

        current_time += datetime.timedelta(hours=1)

        if len(batch_data) >= 3000:
            session.bulk_save_objects(batch_data)
            session.commit()
            batch_data = []

    if batch_data:
        session.bulk_save_objects(batch_data)
        session.commit()

    session.close()
    print("Database seeding completed.")

    # Synchronize instance/dtcm.db as well
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile('dtcm.db', 'instance/dtcm.db')
    print("Synchronized with instance/dtcm.db successfully.")

if __name__ == "__main__":
    generate_indian_sensor_data()
