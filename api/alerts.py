from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app_db import db
from db.models import Alerts, EnvironmentalData, SensorData
from api.data import check_role

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/active', methods=['GET'])
def get_active_alerts():
    alerts = db.session.query(Alerts, EnvironmentalData, SensorData).join(
        EnvironmentalData, Alerts.DataID == EnvironmentalData.DataID
    ).join(
        SensorData, EnvironmentalData.SensorID == SensorData.SensorID
    ).filter(Alerts.Status == 'Active').order_by(Alerts.AlertTime.desc()).all()
    
    result = []
    for alert, data, sensor in alerts:
        result.append({
            "id": alert.AlertID,
            "sensor_id": sensor.SensorID,
            "location": sensor.Location,
            "type": alert.AlertType,
            "message": alert.Message,
            "co2": data.CO2Level,
            "time": alert.AlertTime.isoformat(),
            "status": alert.Status
        })
    return jsonify(result)

@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['PUT'])
@jwt_required()
def acknowledge_alert(alert_id):
    if not check_role(['administrator', 'environmental_authority']):
        return jsonify({"msg": "Unauthorized"}), 403
        
    alert = db.session.query(Alerts).get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
        
    alert.Status = 'Acknowledged'
    db.session.commit()
    
    return jsonify({"msg": "Alert acknowledged"})

@alerts_bp.route('/history', methods=['GET'])
def get_alert_history():
    alerts = db.session.query(Alerts, EnvironmentalData, SensorData).join(
        EnvironmentalData, Alerts.DataID == EnvironmentalData.DataID
    ).join(
        SensorData, EnvironmentalData.SensorID == SensorData.SensorID
    ).order_by(Alerts.AlertTime.desc()).limit(100).all()
    
    result = []
    for alert, data, sensor in alerts:
        result.append({
            "id": alert.AlertID,
            "sensor_id": sensor.SensorID,
            "location": sensor.Location,
            "type": alert.AlertType,
            "message": alert.Message,
            "co2": data.CO2Level,
            "time": alert.AlertTime.isoformat(),
            "status": alert.Status
        })
    return jsonify(result)
