"""
Predictions API Blueprint for DTCM.
Provides routes for ML model inferences and predictions history.
"""
from typing import Tuple, Union
import logging
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import db, User, PredictionResult

predictions_bp = Blueprint('predictions_bp', __name__)
logger = logging.getLogger(__name__)

# Attempt to load the ModelManager at module level
model_manager = None
try:
    from ml.model_manager import ModelManager
    model_manager = ModelManager()
except ImportError:
    logger.warning("Could not import ModelManager module.")
except Exception as e:
    logger.warning(f"Error initializing ModelManager: {e}")

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

def check_model_manager() -> Union[Tuple[Response, int], None]:
    """Helper to check if models are loaded."""
    if model_manager is None:
        return jsonify({"error": "ML Models are currently not loaded or unavailable."}), 503
    return None

@predictions_bp.route('/predict/short-term', methods=['POST'])
@jwt_required()
@role_at_least('researcher')
def predict_short_term() -> Tuple[Response, int]:
    """
    Generate short-term CO2 predictions.
    
    Returns:
        JSON response containing prediction results.
    """
    err = check_model_manager()
    if err:
        return err
        
    data = request.json
    if not data:
        return jsonify({"error": "No JSON input data provided"}), 400
        
    try:
        # Generate prediction using the loaded model manager
        prediction = model_manager.predict_short_term(data)
        return jsonify({"prediction": prediction}), 200
    except Exception as e:
        logger.error(f"Short-term prediction failed: {e}")
        return jsonify({"error": "Prediction processing failed."}), 500

@predictions_bp.route('/predict/long-term', methods=['POST'])
@jwt_required()
@role_at_least('researcher')
def predict_long_term() -> Tuple[Response, int]:
    """
    Generate long-term CO2 predictions.
    
    Returns:
        JSON response containing long-term prediction results.
    """
    err = check_model_manager()
    if err:
        return err
        
    data = request.json
    if not data:
        return jsonify({"error": "No JSON input data provided"}), 400
        
    try:
        prediction = model_manager.predict_long_term(data)
        return jsonify({"prediction": prediction}), 200
    except Exception as e:
        logger.error(f"Long-term prediction failed: {e}")
        return jsonify({"error": "Prediction processing failed."}), 500

@predictions_bp.route('/classify/zones', methods=['POST'])
@jwt_required()
def classify_zones() -> Tuple[Response, int]:
    """
    Classify zones based on environmental parameters.
    
    Returns:
        JSON response with zone classification results.
    """
    err = check_model_manager()
    if err:
        return err
        
    data = request.json
    if not data:
        return jsonify({"error": "No JSON input data provided"}), 400
        
    try:
        classification = model_manager.classify_zones(data)
        return jsonify({"classification": classification}), 200
    except Exception as e:
        logger.error(f"Zone classification failed: {e}")
        return jsonify({"error": "Classification processing failed."}), 500

@predictions_bp.route('/predictions/history', methods=['GET'])
@jwt_required()
def predictions_history() -> Tuple[Response, int]:
    """
    Get a paginated history of predictions.
    
    Returns:
        JSON response with paginated prediction history.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = PredictionResult.query.order_by(PredictionResult.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    data = [{
        "id": item.id,
        "sensor_id": item.sensor_id,
        "predicted_co2": item.predicted_co2,
        "prediction_time": item.prediction_time.isoformat() if item.prediction_time else None,
        "timestamp": item.timestamp.isoformat() if item.timestamp else None
    } for item in pagination.items]
    
    return jsonify({
        "data": data,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page
    }), 200


