"""
Alerts API Blueprint for DTCM.
Provides routes to manage and view system Alert.
"""
from typing import Tuple
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import db, User, Alert

alerts_bp = Blueprint('alerts_bp', __name__)

def role_at_least(required_role: str):
    """
    Decorator to enforce role-based access control.
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

@alerts_bp.route('/active', methods=['GET'])
@jwt_required()
def active_alerts() -> Tuple[Response, int]:
    """
    Fetch all active, unacknowledged Alert.
    
    Returns:
        JSON response with a list of active Alert.
    """
    # Query Alert where status is 'active'
    alerts = Alert.query.filter_by(status='active').order_by(Alert.alert_time.desc()).all()
    data = [{
        "alert_id": alert.alert_id,
        "message": getattr(alert, 'message', ''),
        "level": getattr(alert, 'level', 'Warning'),
        "timestamp": alert.alert_time.isoformat() if alert.alert_time else None
    } for alert in alerts]
    return jsonify(data), 200

@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['PUT'])
@jwt_required()
@role_at_least('administrator')
def acknowledge_alert(alert_id: int) -> Tuple[Response, int]:
    """
    Acknowledge an active alert, updating its status.
    
    Args:
        alert_id (int): The ID of the alert to acknowledge.
        
    Returns:
        JSON response confirming acknowledgment.
    """
    alerts = Alert.query.get_or_404(alert_id)
    
    # Check if already acknowledged
    if alert.status == 'acknowledged':
        return jsonify({"message": f"Alert {alert_id} is already acknowledged."}), 200
        
    alert.status = 'acknowledged'
    db.session.commit()
    
    return jsonify({"message": f"Alert {alert_id} acknowledged successfully."}), 200

@alerts_bp.route('/history', methods=['GET'])
@jwt_required()
def alert_history() -> Tuple[Response, int]:
    """
    Get a paginated history of all Alert.
    
    Returns:
        JSON response containing paginated alert records.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = Alert.query.order_by(Alert.alert_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    data = [{
        "id": item.id,
        "message": getattr(item, 'message', ''),
        "level": getattr(item, 'level', 'Warning'),
        "status": getattr(item, 'status', 'active'),
        "timestamp": item.timestamp.isoformat() if item.timestamp else None
    } for item in pagination.items]
    
    return jsonify({
        "data": data,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page
    }), 200



