from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import pandas as pd
import datetime
from sqlalchemy import func
from app_db import db
from db.models import EnvironmentalData, SensorData, Users

data_bp = Blueprint('data', __name__)

def check_role(allowed_roles):
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return False
    try:
        user = db.session.get(Users, int(current_user_id))
    except (ValueError, TypeError):
        user = None
    if not user or user.Role not in allowed_roles:
        return False
    return True

@data_bp.route('/live', methods=['GET'])
@data_bp.route('/latest', methods=['GET'])
def get_live_data():
    # Latest reading for each sensor (unique by max DataID)
    subquery = db.session.query(
        EnvironmentalData.SensorID,
        func.max(EnvironmentalData.DataID).label('max_id')
    ).group_by(EnvironmentalData.SensorID).subquery()

    latest_data = db.session.query(EnvironmentalData, SensorData).join(
        SensorData, EnvironmentalData.SensorID == SensorData.SensorID
    ).join(
        subquery, 
        EnvironmentalData.DataID == subquery.c.max_id
    ).order_by(SensorData.SensorID).all()

    result = []
    for data, sensor in latest_data:
        result.append({
            "sensor_id": sensor.SensorID,
            "location": sensor.Location,
            "co2": data.CO2Level,
            "temperature": data.Temperature,
            "humidity": data.Humidity,
            "pm25": data.PM2S,
            "aqi": data.AQI,
            "timestamp": data.Timestamp.isoformat()
        })
    return jsonify(result)

@data_bp.route('/history', methods=['GET'])
def get_history():
    sensor_id = request.args.get('sensor_id')
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    hours = request.args.get('hours', type=int)
    limit = request.args.get('limit', type=int)
    aggregate = request.args.get('aggregate', '').lower()
    
    max_limit = limit if limit else (hours if hours else 24)

    # 1. Single sensor specific history
    if sensor_id:
        try:
            s_id = int(sensor_id)
        except (ValueError, TypeError):
            s_id = None
            
        query = db.session.query(EnvironmentalData)
        if s_id is not None:
            query = query.filter_by(SensorID=s_id)
        if start_str:
            query = query.filter(EnvironmentalData.Timestamp >= datetime.datetime.fromisoformat(start_str))
        if end_str:
            query = query.filter(EnvironmentalData.Timestamp <= datetime.datetime.fromisoformat(end_str))
            
        rows = query.order_by(EnvironmentalData.Timestamp.desc()).limit(max_limit).all()
        rows.reverse()
        
        result = []
        for data in rows:
            ts = data.Timestamp.isoformat() if data.Timestamp else ""
            result.append({
                "sensor_id": data.SensorID,
                "co2": round(float(data.CO2Level), 2),
                "CO2Level": round(float(data.CO2Level), 2),
                "temperature": round(float(data.Temperature), 1) if data.Temperature is not None else None,
                "Temperature": round(float(data.Temperature), 1) if data.Temperature is not None else None,
                "humidity": round(float(data.Humidity), 1) if data.Humidity is not None else None,
                "Humidity": round(float(data.Humidity), 1) if data.Humidity is not None else None,
                "pm25": round(float(data.PM2S), 1) if data.PM2S is not None else None,
                "PM2S": round(float(data.PM2S), 1) if data.PM2S is not None else None,
                "aqi": round(float(data.AQI), 1) if data.AQI is not None else None,
                "AQI": round(float(data.AQI), 1) if data.AQI is not None else None,
                "timestamp": ts,
                "Timestamp": ts
            })
        return jsonify(result)

    # 2. Raw unaggregated multi-sensor history if explicitly requested
    if aggregate == 'raw':
        query = db.session.query(EnvironmentalData)
        if start_str:
            query = query.filter(EnvironmentalData.Timestamp >= datetime.datetime.fromisoformat(start_str))
        if end_str:
            query = query.filter(EnvironmentalData.Timestamp <= datetime.datetime.fromisoformat(end_str))
        rows = query.order_by(EnvironmentalData.Timestamp.desc()).limit(max_limit).all()
        rows.reverse()
        result = []
        for data in rows:
            ts = data.Timestamp.isoformat() if data.Timestamp else ""
            result.append({
                "sensor_id": data.SensorID,
                "co2": round(float(data.CO2Level), 2),
                "CO2Level": round(float(data.CO2Level), 2),
                "temperature": round(float(data.Temperature), 1) if data.Temperature is not None else None,
                "Temperature": round(float(data.Temperature), 1) if data.Temperature is not None else None,
                "humidity": round(float(data.Humidity), 1) if data.Humidity is not None else None,
                "Humidity": round(float(data.Humidity), 1) if data.Humidity is not None else None,
                "pm25": round(float(data.PM2S), 1) if data.PM2S is not None else None,
                "PM2S": round(float(data.PM2S), 1) if data.PM2S is not None else None,
                "aqi": round(float(data.AQI), 1) if data.AQI is not None else None,
                "AQI": round(float(data.AQI), 1) if data.AQI is not None else None,
                "timestamp": ts,
                "Timestamp": ts
            })
        return jsonify(result)

    # 3. National Mean Aggregation (per minute bucket, deduplicating x-axis timestamps)
    dialect_name = db.engine.dialect.name
    if dialect_name == 'sqlite':
        time_bucket = func.strftime('%Y-%m-%d %H:%M:00', EnvironmentalData.Timestamp)
    else:
        time_bucket = func.date_trunc('minute', EnvironmentalData.Timestamp)

    subq = db.session.query(
        time_bucket.label('bucket'),
        func.avg(EnvironmentalData.CO2Level).label('co2'),
        func.avg(EnvironmentalData.Temperature).label('temperature'),
        func.avg(EnvironmentalData.Humidity).label('humidity'),
        func.avg(EnvironmentalData.PM2S).label('pm25'),
        func.avg(EnvironmentalData.AQI).label('aqi'),
        func.count(EnvironmentalData.DataID).label('station_count')
    )
    if start_str:
        subq = subq.filter(EnvironmentalData.Timestamp >= datetime.datetime.fromisoformat(start_str))
    if end_str:
        subq = subq.filter(EnvironmentalData.Timestamp <= datetime.datetime.fromisoformat(end_str))

    subq = subq.group_by('bucket').order_by(time_bucket.desc()).limit(max_limit)
    rows = subq.all()
    rows.reverse()

    result = []
    for r in rows:
        ts_val = r.bucket
        if isinstance(ts_val, datetime.datetime):
            ts_iso = ts_val.isoformat()
        else:
            try:
                ts_iso = datetime.datetime.fromisoformat(str(ts_val)).isoformat()
            except Exception:
                ts_iso = str(ts_val)

        result.append({
            "sensor_id": "national_mean",
            "co2": round(float(r.co2), 2) if r.co2 is not None else 0.0,
            "CO2Level": round(float(r.co2), 2) if r.co2 is not None else 0.0,
            "temperature": round(float(r.temperature), 1) if r.temperature is not None else None,
            "Temperature": round(float(r.temperature), 1) if r.temperature is not None else None,
            "humidity": round(float(r.humidity), 1) if r.humidity is not None else None,
            "Humidity": round(float(r.humidity), 1) if r.humidity is not None else None,
            "pm25": round(float(r.pm25), 1) if r.pm25 is not None else None,
            "PM2S": round(float(r.pm25), 1) if r.pm25 is not None else None,
            "aqi": round(float(r.aqi), 1) if r.aqi is not None else None,
            "AQI": round(float(r.aqi), 1) if r.aqi is not None else None,
            "timestamp": ts_iso,
            "Timestamp": ts_iso,
            "station_count": r.station_count
        })
    return jsonify(result)

@data_bp.route('/hotspots', methods=['GET'])
def get_hotspots():
    # Top 5 zones by latest CO2
    subquery = db.session.query(
        EnvironmentalData.SensorID,
        func.max(EnvironmentalData.Timestamp).label('max_time')
    ).group_by(EnvironmentalData.SensorID).subquery()

    latest_data = db.session.query(EnvironmentalData, SensorData).join(
        SensorData, EnvironmentalData.SensorID == SensorData.SensorID
    ).join(
        subquery, 
        (EnvironmentalData.SensorID == subquery.c.SensorID) & 
        (EnvironmentalData.Timestamp == subquery.c.max_time)
    ).order_by(EnvironmentalData.CO2Level.desc()).limit(5).all()

    result = []
    for data, sensor in latest_data:
        result.append({
            "sensor_id": sensor.SensorID,
            "location": sensor.Location,
            "co2": data.CO2Level,
            "timestamp": data.Timestamp.isoformat()
        })
    return jsonify(result)

@data_bp.route('/template/csv', methods=['GET'])
def download_csv_template():
    import io, csv
    from flask import make_response
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['sensor_id', 'co2', 'temp', 'humidity', 'pm25', 'aqi', 'timestamp'])
    sample_time = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for i in range(6):
        t = sample_time - datetime.timedelta(hours=i)
        cw.writerow([
            (i % 6) + 1,
            round(425.0 + (i * 4.5), 1),
            round(28.0 - (i * 0.3), 1),
            round(60.0 + (i * 1.2), 1),
            round(42.0 + (i * 2.0), 1),
            round(110.0 + (i * 3.0), 0),
            t.strftime('%Y-%m-%d %H:%M:%S')
        ])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=dtcm_telemetry_template.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@data_bp.route('/import/csv', methods=['POST'])
@jwt_required(optional=True)
def import_csv():
    current_user_id = get_jwt_identity()
    if current_user_id:
        if not check_role(['administrator', 'researcher', 'environmental_authority', 'general']):
            return jsonify({"msg": "Unauthorized"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "No file part in upload request."}), 400
        
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No CSV file selected."}), 400
        
    try:
        df = pd.read_csv(file)
        if df.empty:
            return jsonify({"error": "The uploaded CSV file contains no data rows."}), 400

        # Clean column names: strip whitespace
        df.columns = [str(c).strip() for c in df.columns]

        # Flexible alias mapping for column names
        alias_map = {
            'sensor_id': ['sensor_id', 'sensorid', 'sensor', 'station_id', 'stationid', 'station', 'node_id', 'node'],
            'co2': ['co2', 'co2level', 'co2_level', 'co2_ppm', 'co2ppm', 'carbon_dioxide', 'co2_concentration', 'co2level_ppm', 'co2_reading'],
            'temp': ['temp', 'temperature', 'ambient_temp', 'ambient_temperature', 'temp_c', 'temperature_c', 't'],
            'humidity': ['humidity', 'rh', 'relative_humidity', 'rel_humidity', 'hum', 'humidity_pct', 'humidity_%'],
            'pm25': ['pm25', 'pm2_5', 'pm2s', 'pm2.5', 'pm_25', 'particulate_matter_25', 'pm25_ugm3'],
            'aqi': ['aqi', 'air_quality_index', 'aqi_score', 'aqi_value', 'composite_aqi'],
            'timestamp': ['timestamp', 'datetime', 'date', 'time', 'ts', 'recorded_at', 'reading_time', 'time_stamp', 'date_time']
        }

        matched_cols = {}
        for canonical, aliases in alias_map.items():
            for orig_col in df.columns:
                norm = orig_col.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
                if norm in aliases or orig_col.lower() in aliases:
                    matched_cols[canonical] = orig_col
                    break

        # Mandatory check: at least CO2 must be present
        if 'co2' not in matched_cols:
            return jsonify({
                "error": "Missing CO2 concentration column. Expected one of: 'co2', 'CO2Level', 'co2_ppm', or 'co2_level'."
            }), 400

        existing_sensors = {s.SensorID for s in db.session.query(SensorData.SensorID).all()}
        now = datetime.datetime.utcnow()
        data_objs = []
        new_sensors_created = set()

        for idx, row in df.iterrows():
            # Sensor ID
            s_val = row[matched_cols['sensor_id']] if 'sensor_id' in matched_cols else 1
            try:
                s_id = int(s_val) if pd.notnull(s_val) else 1
            except (ValueError, TypeError):
                s_id = 1

            if s_id not in existing_sensors and s_id not in new_sensors_created:
                new_s = SensorData(SensorID=s_id, Location=f"Telemetry Station #{s_id}", Type="CO2")
                db.session.add(new_s)
                new_sensors_created.add(s_id)

            # CO2
            co2_raw = row[matched_cols['co2']]
            try:
                co2_val = float(co2_raw) if pd.notnull(co2_raw) else None
            except (ValueError, TypeError):
                co2_val = None

            if co2_val is None:
                continue

            # Temperature
            temp_raw = row[matched_cols['temp']] if 'temp' in matched_cols else None
            try:
                temp_val = float(temp_raw) if pd.notnull(temp_raw) else 27.5
            except (ValueError, TypeError):
                temp_val = 27.5

            # Humidity
            hum_raw = row[matched_cols['humidity']] if 'humidity' in matched_cols else None
            try:
                hum_val = float(hum_raw) if pd.notnull(hum_raw) else 60.0
            except (ValueError, TypeError):
                hum_val = 60.0

            # PM2.5
            pm25_raw = row[matched_cols['pm25']] if 'pm25' in matched_cols else None
            try:
                pm25_val = float(pm25_raw) if pd.notnull(pm25_raw) else 45.0
            except (ValueError, TypeError):
                pm25_val = 45.0

            # AQI
            aqi_raw = row[matched_cols['aqi']] if 'aqi' in matched_cols else None
            try:
                aqi_val = float(aqi_raw) if pd.notnull(aqi_raw) else round((pm25_val * 2.2) + max(0.0, co2_val - 400.0) * 0.25)
            except (ValueError, TypeError):
                aqi_val = 110.0

            # Timestamp
            if 'timestamp' in matched_cols and pd.notnull(row[matched_cols['timestamp']]):
                try:
                    ts_val = pd.to_datetime(row[matched_cols['timestamp']]).to_pydatetime()
                except Exception:
                    ts_val = now - datetime.timedelta(minutes=(len(df) - idx) * 15)
            else:
                ts_val = now - datetime.timedelta(minutes=(len(df) - idx) * 15)

            data_objs.append(EnvironmentalData(
                SensorID=s_id,
                CO2Level=co2_val,
                Temperature=temp_val,
                Humidity=hum_val,
                PM2S=pm25_val,
                AQI=aqi_val,
                Timestamp=ts_val
            ))

        if not data_objs:
            return jsonify({"error": "No valid numerical telemetry rows found in CSV."}), 400

        # Bulk insert
        db.session.bulk_save_objects(data_objs)
        db.session.commit()

        # Sync state with digital twin engine
        try:
            from twin.engine import twin_engine
            twin_engine.sync_state()
        except Exception:
            pass

        return jsonify({
            "msg": f"Successfully parsed and ingested {len(data_objs)} telemetry recordings.",
            "rows_imported": len(data_objs),
            "matched_schema": {k: matched_cols[k] for k in matched_cols}
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to parse CSV: {str(e)}"}), 500
