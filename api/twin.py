from flask import Blueprint, request, jsonify
from twin.engine import twin_engine
from app_db import db
from db.models import SimulationResults

twin_bp = Blueprint('twin', __name__)

@twin_bp.route('/state', methods=['GET'])
def get_state():
    return jsonify(twin_engine.state)

@twin_bp.route('/simulate', methods=['POST'])
def simulate():
    params = request.get_json()
    if not params:
        return jsonify({"error": "No parameters provided"}), 400
        
    result = twin_engine.simulate_scenario(params)
    return jsonify(result)

@twin_bp.route('/simulations', methods=['GET'])
def list_simulations():
    sims = db.session.query(SimulationResults).order_by(SimulationResults.SimTime.desc()).limit(50).all()
    results = []
    for s in sims:
        results.append({
            "id": s.SimID,
            "scenario": s.ScenarioName,
            "simulated_co2": s.SimulatedCO2,
            "parameters": s.Parameters,
            "time": s.SimTime.isoformat()
        })
    return jsonify(results)
    
@twin_bp.route('/optimizer', methods=['GET'])
def get_optimizer():
    return jsonify({"recommendations": twin_engine.optimize_capture_placement()})

@twin_bp.route('/hotspots', methods=['GET'])
def get_hotspots():
    hotspots = twin_engine.get_hotspots()
    results = []
    for s_id, s_data in hotspots:
        results.append({
            "sensor_id": s_id,
            "location": s_data.get("location", f"Station {s_id}"),
            "latest_co2": s_data.get("latest_co2"),
            "predicted_co2": s_data.get("predicted_co2"),
            "zone_class": s_data.get("zone_class"),
            "temperature": s_data.get("temperature"),
            "pm25": s_data.get("pm25")
        })
    return jsonify({"hotspots": results})

