"""
Digital Twin API Blueprint for DTCM.
Provides routes to interact with the Digital Twin Engine.
"""
import json
from typing import Tuple
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import db, User, SimulationResult

twin_bp = Blueprint('twin_bp', __name__)

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

@twin_bp.route('/state', methods=['GET'])
@jwt_required()
def get_twin_state() -> Tuple[Response, int]:
    """
    Get the current state of the digital twin.
    
    Returns:
        JSON response with the active status and sync information.
    """
    # Assuming a dynamic or static state representation
    state = {
        "status": "active",
        "sync_rate": "1s",
        "last_sync": "2023-10-10T12:00:00Z"
    }
    return jsonify(state), 200

@twin_bp.route('/simulate', methods=['POST'])
@jwt_required()
@role_at_least('researcher')
def simulate() -> Tuple[Response, int]:
    """
    Trigger a new simulation using specified parameters.
    
    Returns:
        JSON response acknowledging simulation execution.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Simulation parameters are required"}), 400
        
    try:
        # Mocking simulation creation and persisting to database
        sim_result = SimulationResult(
            parameters=json.dumps(data),
            result_data=json.dumps({"status": "completed", "mock_metric": 0.99})
        )
        db.session.add(sim_result)
        db.session.commit()
        
        return jsonify({
            "message": "Simulation executed successfully.",
            "simulation_id": sim_result.id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500

@twin_bp.route('/simulations', methods=['GET'])
@jwt_required()
def get_simulations() -> Tuple[Response, int]:
    """
    Retrieve all previous simulation results.
    
    Returns:
        JSON response with a list of past simulations.
    """
    simulations = SimulationResult.query.all()
    data = [{
        "id": sim.id,
        "parameters": json.loads(sim.parameters) if sim.parameters else {},
        "result_data": json.loads(sim.result_data) if sim.result_data else {},
        # Ensure timestamp serialization if the model provides it
        "timestamp": getattr(sim, 'timestamp').isoformat() if hasattr(sim, 'timestamp') and sim.timestamp else None
    } for sim in simulations]
    return jsonify(data), 200


