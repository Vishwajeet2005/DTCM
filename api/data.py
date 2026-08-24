"""
Data API Blueprint for DTCM.
Provides routes for fetching environmental data and importing from CSV.
"""
from typing import Tuple
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import db, SensorData, EnvironmentalData, User
from ingestion.csv_importer import CSVImporter

data_bp = Blueprint('data_bp', __name__)

def get_severity_label(co2: float, warning: float = 450.0, critical: float = 500.0) -> str:
    """
    Determine severity label based on CO2 level Threshold.
    
    Args:
        co2 (float): The measured CO2 level in ppm.
        warning (float): The threshold for a warning label.
        critical (float): The threshold for a critical label.
        
    Returns:
        str: 'Critical', 'Warning', or 'Normal'.
    """
    if co2 >= critical:
        return 'Critical'
    elif co2 >= warning:
        return 'Warning'
    return 'Normal'

def role_at_least(required_role: str):
    """
    Decorator to enforce role-based access control.
    
    Args:
        required_role (str): Minimum role required (general, researcher, administrator, environmental_authority).
    """
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Tuple[Response, int]:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            roles = ['general', 'researcher', 'administrator', 'environmental_authority']
            try:
                user_rank = roles.index(user.role)
                required_rank = roles.index(required_role)
            except ValueError:
                return jsonify({"error": "Invalid role configured"}), 500
                
            if user_rank < required_rank:
                return jsonify({"error": "Insufficient privileges"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@data_bp.route('/live', methods=['GET'])
@jwt_required()
def get_live_data() -> Tuple[Response, int]:
    """
    Return the latest reading per sensor along with its name and severity label.
    
    Returns:
        JSON response containing a list of the latest sensor readings.
    """
    sensors = SensorData.query.all()
    results = []
    
    for sensor in sensors:
        # Retrieve the most recent reading for each sensor
        latest = EnvironmentalData.query.filter_by(sensor_id=sensor.sensor_id).order_by(EnvironmentalData.timestamp.desc()).first()
        if latest:
            # Assume configurable Threshold might be applied here per zone if available
            results.append({
                "sensor_id": sensor.sensor_id,
                "sensor_name": sensor.location,
                "co2_level": latest.co2_level,
                "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
                "severity_label": get_severity_label(latest.co2_level)
            })
            
    return jsonify(results), 200

@data_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history_data() -> Tuple[Response, int]:
    """
    Provide a paginated list of EnvironmentalData rows.
    
    Returns:
        JSON response with paginated historical data.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = EnvironmentalData.query.order_by(EnvironmentalData.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    data = [{
        "data_id": item.data_id,
        "sensor_id": item.sensor_id,
        "co2_level": item.co2_level,
        "temperature": getattr(item, 'temperature', None),
        "humidity": getattr(item, 'humidity', None),
        "timestamp": item.timestamp.isoformat() if item.timestamp else None
    } for item in pagination.items]
    
    return jsonify({
        "data": data,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page
    }), 200

@data_bp.route('/hotspots', methods=['GET'])
@jwt_required()
def get_hotspots() -> Tuple[Response, int]:
    """
    Get the top 5 sensors by the latest CO2 reading to identify hotspots.
    
    Returns:
        JSON response with the top 5 highest CO2 readings.
    """
    sensors = SensorData.query.all()
    latest_readings = []
    
    for sensor in sensors:
        latest = EnvironmentalData.query.filter_by(sensor_id=sensor.sensor_id).order_by(EnvironmentalData.timestamp.desc()).first()
        if latest:
            latest_readings.append({
                "sensor_id": sensor.sensor_id,
                "sensor_name": sensor.location,
                "co2_level": latest.co2_level,
                "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
                "severity_label": get_severity_label(latest.co2_level)
            })
            
    # Sort descending by CO2 level and take top 5
    latest_readings.sort(key=lambda x: x['co2_level'], reverse=True)
    return jsonify(latest_readings[:5]), 200

@data_bp.route('/import/csv', methods=['POST'])
@jwt_required()
@role_at_least('researcher')
def import_csv() -> Tuple[Response, int]:
    """
    Handle CSV file uploads to bulk import historical data.
    Requires at least 'researcher' role.
    
    Returns:
        JSON response indicating success or failure of the import.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400
    
    if file and file.filename.endswith('.csv'):
        try:
            # Instantiate importer and process the uploaded file
            importer = CSVImporter()
            importer.import_data(file)
            return jsonify({"message": "CSV data imported successfully"}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to import CSV: {str(e)}"}), 500
            
    return jsonify({"error": "Invalid file type. Only .csv files are allowed."}), 400




