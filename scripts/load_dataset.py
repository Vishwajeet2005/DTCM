"""
load_dataset.py
===============
Utility script to load an environmental telemetry dataset CSV into DTCM database.
Allows using offline datasets (CPCB / Kaggle / EPA) instead of external APIs.
"""

import os
import sys
import argparse
import datetime
import shutil
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import BASE_DIR, DEFAULT_DB_PATH, DEFAULT_DB_URI
from db.models import Base, SensorData, EnvironmentalData
from twin.engine import twin_engine

# Canonical sensor metadata for default stations
DEFAULT_STATIONS = [
    (1, "Anand Vihar ISBT, New Delhi", "NDIR CO2 & CPCB AQI"),
    (2, "Bandra-Kurla Complex (BKC), Mumbai", "Optical CO2 & MPCB Telemetry"),
    (3, "Peenya Industrial Area, Bengaluru", "Electrochemical & KSPCB Monitor"),
    (4, "Okhla Industrial Area Phase-III, New Delhi", "NDIR Industrial Sensor"),
    (5, "Manali Petrochemical Corridor, Chennai", "Infrared Gas Sensor"),
    (6, "Sector V, Salt Lake, Kolkata", "Laser Particle & CO2 Sensor")
]

ALIAS_MAP = {
    'sensor_id': 'sensor_id', 'sensorid': 'sensor_id', 'station_id': 'sensor_id',
    'location': 'location', 'station': 'location', 'station_name': 'location',
    'co2': 'co2', 'co2level': 'co2', 'co2_level': 'co2', 'co2_ppm': 'co2',
    'temp': 'temp', 'temperature': 'temp', 'temp_c': 'temp',
    'humidity': 'humidity', 'rh': 'humidity', 'relative_humidity': 'humidity',
    'pm25': 'pm25', 'pm2s': 'pm25', 'pm2_5': 'pm25', 'pm25_ugm3': 'pm25',
    'aqi': 'aqi', 'air_quality_index': 'aqi',
    'timestamp': 'timestamp', 'datetime': 'timestamp', 'date': 'timestamp'
}

def load_dataset(csv_path: str, clear_existing: bool = False, batch_size: int = 5000):
    if not os.path.exists(csv_path):
        print(f"Error: Dataset file not found at: {csv_path}")
        sys.exit(1)

    print(f"Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Read {len(df)} rows. Columns: {list(df.columns)}")

    # Header normalization
    matched_cols = {}
    for col in df.columns:
        clean = col.strip().lower().replace(' ', '_').replace('.', '')
        if clean in ALIAS_MAP:
            matched_cols[ALIAS_MAP[clean]] = col

    if 'co2' not in matched_cols:
        print("Error: Missing CO2 concentration column in dataset CSV.")
        sys.exit(1)

    engine = create_engine(DEFAULT_DB_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Ensure baseline stations exist
    existing_sensor_ids = {s.SensorID for s in session.query(SensorData.SensorID).all()}
    for sid, loc, stype in DEFAULT_STATIONS:
        if sid not in existing_sensor_ids:
            session.add(SensorData(SensorID=sid, Location=loc, Type=stype, Status="Active"))
            existing_sensor_ids.add(sid)
    session.commit()

    if clear_existing:
        print("Clearing existing EnvironmentalData table...")
        session.query(EnvironmentalData).delete()
        session.commit()

    # Prepare data objects
    sensor_col = matched_cols.get('sensor_id')
    location_col = matched_cols.get('location')
    co2_col = matched_cols.get('co2')
    temp_col = matched_cols.get('temp')
    hum_col = matched_cols.get('humidity')
    pm25_col = matched_cols.get('pm25')
    aqi_col = matched_cols.get('aqi')
    ts_col = matched_cols.get('timestamp')

    data_objs = []
    print("Ingesting records into database...")

    for _, row in df.iterrows():
        # Sensor ID
        sid = 1
        if sensor_col and pd.notna(row.get(sensor_col)):
            try:
                sid = int(row[sensor_col])
            except (ValueError, TypeError):
                sid = 1

        if sid not in existing_sensor_ids:
            loc_name = str(row.get(location_col, f"Station #{sid}")) if location_col else f"Station #{sid}"
            new_sensor = SensorData(SensorID=sid, Location=loc_name, Type="Dataset Imported Node", Status="Active")
            session.add(new_sensor)
            session.flush()
            existing_sensor_ids.add(sid)

        # CO2
        try:
            co2_val = float(row[co2_col])
        except (ValueError, TypeError):
            continue

        # Optional metrics
        temp_val = float(row[temp_col]) if temp_col and pd.notna(row.get(temp_col)) else None
        hum_val = float(row[hum_col]) if hum_col and pd.notna(row.get(hum_col)) else None
        pm25_val = float(row[pm25_col]) if pm25_col and pd.notna(row.get(pm25_col)) else None
        aqi_val = float(row[aqi_col]) if aqi_col and pd.notna(row.get(aqi_col)) else None

        # Timestamp
        ts_val = None
        if ts_col and pd.notna(row.get(ts_col)):
            try:
                ts_val = pd.to_datetime(row[ts_col]).to_pydatetime()
            except Exception:
                ts_val = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        else:
            ts_val = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        entry = EnvironmentalData(
            SensorID=sid,
            CO2Level=round(co2_val, 2),
            Temperature=round(temp_val, 1) if temp_val is not None else 25.0,
            Humidity=round(hum_val, 1) if hum_val is not None else 50.0,
            PM2S=round(pm25_val, 1) if pm25_val is not None else 40.0,
            AQI=round(aqi_val, 1) if aqi_val is not None else 100.0,
            Timestamp=ts_val,
            data_gap=False
        )
        data_objs.append(entry)

        if len(data_objs) >= batch_size:
            session.bulk_save_objects(data_objs)
            session.commit()
            print(f"  Inserted {batch_size} rows...")
            data_objs = []

    if data_objs:
        session.bulk_save_objects(data_objs)
        session.commit()
        print(f"  Inserted final {len(data_objs)} rows...")

    session.close()
    twin_engine.sync_state()

    # Mirror to instance/dtcm.db for consistency
    instance_db = os.path.join(BASE_DIR, 'instance', 'dtcm.db')
    if os.path.exists(DEFAULT_DB_PATH):
        os.makedirs(os.path.dirname(instance_db), exist_ok=True)
        shutil.copyfile(DEFAULT_DB_PATH, instance_db)

    print(f"\nSuccessfully loaded dataset into DTCM database ({DEFAULT_DB_PATH}).")
    print("Digital twin engine synchronized with latest dataset state.")

def main():
    parser = argparse.ArgumentParser(description="Load dataset CSV into DTCM database")
    default_csv = os.path.join(BASE_DIR, 'data', 'cpcb_indian_stations_telemetry.csv')
    parser.add_argument('--file', '-f', default=default_csv, help="Path to dataset CSV file")
    parser.add_argument('--clear', action='store_true', help="Clear existing telemetry data before loading")
    args = parser.parse_args()

    load_dataset(args.file, clear_existing=args.clear)

if __name__ == '__main__':
    main()
