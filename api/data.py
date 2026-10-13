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
    
    query = db.session.query(EnvironmentalData)
    if sensor_id:
        try:
            query = query.filter_by(SensorID=int(sensor_id))
        except (ValueError, TypeError):
            pass
    if start_str:
        query = query.filter(EnvironmentalData.Timestamp >= datetime.datetime.fromisoformat(start_str))
    if end_str:
        query = query.filter(EnvironmentalData.Timestamp <= datetime.datetime.fromisoformat(end_str))
        
    if hours:
        rows = query.order_by(EnvironmentalData.Timestamp.desc()).limit(hours).all()
        rows.reverse()
    elif limit:
        rows = query.order_by(EnvironmentalData.Timestamp.desc()).limit(limit).all()
        rows.reverse()
    elif not start_str and not end_str:
        rows = query.order_by(EnvironmentalData.Timestamp.desc()).limit(24).all()
        rows.reverse()
    else:
        rows = query.order_by(EnvironmentalData.Timestamp.asc()).limit(1000).all()
    
    result = []
    for data in rows:
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
            "timestamp": data.Timestamp.isoformat(),
            "Timestamp": data.Timestamp.isoformat()
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

@data_bp.route('/import/csv', methods=['POST'])
@jwt_required()
def import_csv():
    if not check_role(['administrator', 'researcher', 'environmental_authority']):
        return jsonify({"msg": "Unauthorized"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    try:
        df = pd.read_csv(file)
        # Validate schema
        required_cols = ['sensor_id', 'co2', 'temp', 'humidity', 'pm25', 'aqi', 'timestamp']
        if not all(col in df.columns for col in required_cols):
            return jsonify({"error": f"Missing required columns. Expected: {required_cols}"}), 400
            
        data_objs = []
        for _, row in df.iterrows():
            obj = EnvironmentalData(
                SensorID=row['sensor_id'],
                CO2Level=row['co2'],
                Temperature=row['temp'],
                Humidity=row['humidity'],
                PM2S=row['pm25'],
                AQI=row['aqi'],
                Timestamp=pd.to_datetime(row['timestamp']).to_pydatetime()
            )
            data_objs.append(obj)
            
        # Bulk insert
        db.session.bulk_save_objects(data_objs)
        db.session.commit()
        
        return jsonify({"msg": f"Successfully imported {len(data_objs)} rows."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
