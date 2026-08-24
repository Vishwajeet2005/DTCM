import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
import os
import joblib
import pandas as pd

class DigitalTwinEngine:
    """Maintains a virtual real-time state of all sensor zones. Syncs from DB every 5 minutes."""
    
    def __init__(self, app=None):
        self.state = {}
        self.model_manager = None
        self.app = app
        self._sync_thread = None
        self._last_sync = None
        self.is_running = False
        self.logger = logging.getLogger('DigitalTwinEngine')
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
    
    def sync_state(self):
        """Pull latest readings from DB, update self.state."""
        if not self.app:
            self.logger.error("App context not initialized. Cannot sync state.")
            return
            
        with self.app.app_context():
            try:
                from db.models import db, SensorData
                from sqlalchemy import func
                
                # Fetch the most recent sensor reading for each sensor
                subquery = db.session.query(
                    SensorData.sensor_id, 
                    func.max(SensorData.timestamp).label('max_timestamp')
                ).group_by(SensorData.sensor_id).subquery()
                
                latest_readings = db.session.query(SensorData).join(
                    subquery,
                    (SensorData.sensor_id == subquery.c.sensor_id) & 
                    (SensorData.timestamp == subquery.c.max_timestamp)
                ).all()
                
                for sensor in latest_readings:
                    self.state[sensor.sensor_id] = {
                        'sensor_id': sensor.sensor_id,
                        'co2_level': sensor.co2_level,
                        'temperature': sensor.temperature,
                        'humidity': sensor.humidity,
                        'traffic_density': sensor.traffic_density,
                        'industrial_activity': sensor.industrial_activity,
                        'timestamp': sensor.timestamp
                    }
                
                self._last_sync = datetime.utcnow()
                self.logger.info(f"Twin engine state synchronized at {self._last_sync}.")
            except Exception as e:
                self.logger.error(f"Error synchronizing state: {e}")
    
    def get_state(self) -> dict:
        """Return the current virtual state of the twin."""
        return {
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "zones": list(self.state.values())
        }
    
    def get_hotspots(self, top_n: int = 5) -> list[dict]:
        """Return the top_n zones with the highest CO2 levels."""
        zones = list(self.state.values())
        sorted_zones = sorted(zones, key=lambda x: x.get('co2_level', 0), reverse=True)
        return sorted_zones[:top_n]
    
    def simulate_scenario(self, params: dict) -> dict:
        """Apply traffic/industrial/green adjustments, use RF model for forecast, save to SimulationResults."""
        if not self.app:
            return {"error": "App context not initialized"}
            
        # Defaults
        traffic_adj = float(params.get('traffic_adjustment', 1.0))
        industrial_adj = float(params.get('industrial_adjustment', 1.0))
        green_adj = float(params.get('green_space_adjustment', 1.0))
        
        # Load ML model and scaler
        try:
            base_dir = os.path.dirname(self.app.instance_path) if self.app.instance_path else os.getcwd()
            # fallback to explicit path if instance_path is weird
            if not os.path.exists(os.path.join(base_dir, 'models', 'rf_model.pkl')):
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                
            model_path = os.path.join(base_dir, 'models', 'rf_model.pkl')
            scaler_path = os.path.join(base_dir, 'models', 'scaler.pkl')
            
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
        except Exception as e:
            self.logger.error(f"Failed to load simulation models: {e}")
            return {"error": "Models could not be loaded for simulation."}
            
        results = []
        sim_id = f"sim_{int(time.time())}"
        
        with self.app.app_context():
            from db.models import db, SimulationResults
            import json
            
            for sensor_id, data in self.state.items():
                features = {
                    'temperature': data.get('temperature', 25.0),
                    'humidity': data.get('humidity', 50.0),
                    'traffic_density': data.get('traffic_density', 100) * traffic_adj,
                    'industrial_activity': data.get('industrial_activity', 50) * industrial_adj
                }
                
                df = pd.DataFrame([features])
                scaled = scaler.transform(df)
                pred_co2 = float(model.predict(scaled)[0])
                
                # Apply green space heuristic: 10% increase in green space reduces CO2 by 2%
                green_reduction = (green_adj - 1.0) * 0.2 
                pred_co2 = pred_co2 * (1.0 - green_reduction)
                
                results.append({
                    "sensor_id": sensor_id,
                    "original_co2": float(data.get('co2_level', 0)),
                    "predicted_co2": pred_co2
                })
                
                sim_record = SimulationResults(
                    simulation_id=sim_id,
                    sensor_id=sensor_id,
                    parameters=json.dumps(params), # Store as JSON string if DB schema requires text
                    predicted_co2=pred_co2,
                    timestamp=datetime.utcnow()
                )
                db.session.add(sim_record)
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                self.logger.error(f"Failed to save simulation records: {e}")
                
        return {
            "simulation_id": sim_id,
            "parameters": params,
            "results": results
        }
    
    def get_carbon_capture_recommendations(self) -> list[dict]:
        """Generate recommendations based on current state and hotspots."""
        hotspots = self.get_hotspots(top_n=5)
        recommendations = []
        
        for spot in hotspots:
            co2 = spot.get('co2_level', 0)
            if co2 > 500:
                rec = {
                    "sensor_id": spot['sensor_id'],
                    "priority": "Critical",
                    "action": "Immediate traffic diversion and curtailment of industrial operations.",
                    "expected_impact": "15-20% CO2 reduction in 24 hours."
                }
                recommendations.append(rec)
            elif co2 > 450:
                rec = {
                    "sensor_id": spot['sensor_id'],
                    "priority": "High",
                    "action": "Deploy mobile carbon scrubbers and increase urban green canopy.",
                    "expected_impact": "5-10% CO2 reduction in 7 days."
                }
                recommendations.append(rec)
                
        return recommendations
    
    def _sync_loop(self):
        """Background loop to periodically sync state from DB."""
        while self.is_running:
            self.sync_state()
            # 5 minutes = 300 seconds. Breakable sleep.
            for _ in range(300):
                if not self.is_running:
                    break
                time.sleep(1)
    
    def start_sync(self, app):
        """Start the synchronization background thread."""
        self.init_app(app)
        if self._sync_thread and self._sync_thread.is_alive():
            self.logger.warning("Sync thread already running.")
            return
            
        self.is_running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        self.logger.info("Digital Twin sync thread started.")
        
    def stop_sync(self):
        """Stop the background synchronization thread."""
        self.is_running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=2.0)
            self.logger.info("Digital Twin sync thread stopped.")

twin_engine = DigitalTwinEngine()

