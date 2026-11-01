import os
import sys
import sqlite3
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import BASE_DIR, DEFAULT_DB_PATH

DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_CSV = os.path.join(DATA_DIR, 'cpcb_indian_stations_telemetry.csv')
SAMPLE_CSV = os.path.join(DATA_DIR, 'sample_telemetry_dataset.csv')

def export_db_to_csv():
    print(f"Connecting to database at: {DEFAULT_DB_PATH}")
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    
    query = """
    SELECT 
        e.SensorID AS sensor_id,
        s.Location AS location,
        ROUND(e.CO2Level, 2) AS co2,
        ROUND(e.Temperature, 1) AS temp,
        ROUND(e.Humidity, 1) AS humidity,
        ROUND(e.PM2S, 1) AS pm25,
        ROUND(e.AQI, 1) AS aqi,
        e.Timestamp AS timestamp
    FROM EnvironmentalData e
    LEFT JOIN SensorData s ON e.SensorID = s.SensorID
    ORDER BY e.Timestamp ASC, e.SensorID ASC
    """
    
    print("Exporting environmental telemetry dataset...")
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("Warning: No records found in EnvironmentalData table.")
        return
        
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Successfully exported {len(df)} records to: {OUTPUT_CSV}")
    
    # Also save a 100-row sample for quick inspection/demo
    df_sample = df.tail(100)
    df_sample.to_csv(SAMPLE_CSV, index=False)
    print(f"Successfully exported {len(df_sample)} sample records to: {SAMPLE_CSV}")

if __name__ == '__main__':
    export_db_to_csv()
