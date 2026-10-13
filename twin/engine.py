import threading
import time
import logging
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import config
from db.models import Base, EnvironmentalData, SensorData, SimulationResults
from ml.models import ModelManager
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TwinEngine:
    def __init__(self):
        self.state = {}
        self.engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.model_manager = ModelManager()
        self.model_manager.load_models()
        self.lock = threading.Lock()
        
    METADATA_DEFAULTS = {
        1: {"pop": 16400, "acc": 0.94, "cost": "Tier 1 ($$$)", "tag": "Interstate Transit Terminal & Traffic Inversion", "action": "Deploy Dual Direct Air Capture (DAC) Scrubbers (800t/yr)"},
        2: {"pop": 12800, "acc": 0.95, "cost": "Tier 1 ($$$)", "tag": "Commercial CBD & Arterial Corridor", "action": "Install Rooftop Micro-Algae Photobioreactors & EV Zones"},
        3: {"pop": 7200, "acc": 0.88, "cost": "Tier 2 ($$)", "tag": "Heavy Machinery & Industrial Cluster", "action": "Point-Source Industrial Flue-Gas Scrubbing Units"},
        4: {"pop": 14200, "acc": 0.90, "cost": "Tier 1 ($$$)", "tag": "Industrial Corridor & Urban Fringe", "action": "Deploy Modular Solid-Sorbent DAC Pods (500t/yr)"},
        5: {"pop": 5400, "acc": 0.84, "cost": "Tier 2 ($$)", "tag": "Petrochemical & Refinery Belt", "action": "Chemical Amine Absorption & Carbon Mineralization"},
        6: {"pop": 10500, "acc": 0.86, "cost": "Tier 2 ($$)", "tag": "IT Corridor & Commuter Arterial", "action": "Urban Miyawaki Forest Expansion & Bio-Filters"}
    }

    def sync_state(self):
        session = self.Session()
        try:
            sensors = session.query(SensorData).all()
            with self.lock:
                for sensor in sensors:
                    latest = session.query(EnvironmentalData).filter_by(SensorID=sensor.SensorID).order_by(EnvironmentalData.Timestamp.desc()).first()
                    if latest:
                        meta = self.METADATA_DEFAULTS.get(sensor.SensorID, {"pop": 8500, "acc": 0.85})
                        self.state[sensor.SensorID] = {
                            "location": sensor.Location,
                            "latest_co2": latest.CO2Level,
                            "timestamp": latest.Timestamp.isoformat(),
                            "temperature": latest.Temperature,
                            "humidity": latest.Humidity,
                            "pm25": latest.PM2S,
                            "aqi": latest.AQI,
                            "population_density": meta["pop"],
                            "accessibility": meta["acc"]
                        }
            logger.info("Twin state synchronized.")
        except Exception as e:
            logger.error(f"Error syncing twin state: {e}")
        finally:
            session.close()

    def start_sync_cycle(self):
        def loop():
            while True:
                self.sync_state()
                time.sleep(300) # 5 minutes
        
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def simulate_scenario(self, params: dict) -> dict:
        if not self.state:
            self.sync_state()
            
        traffic_reduction = float(params.get("traffic_reduction_pct", 0) or 0)
        green_increase = float(params.get("green_area_increase_km2", 0) or 0)
        industrial_shutdown = params.get("industrial_shutdown", []) or []
        dac_units = int(params.get("dac_units", 0) or 0)
        duration = int(params.get("duration_hours", 24) or 24)
        scenario_name = params.get("scenario_name", "Scenario Analysis")
        
        baseline = sum(s["latest_co2"] for s in self.state.values()) / max(1, len(self.state)) if self.state else 422.5
        
        # Parametric reduction formula:
        # Traffic: -0.45 ppm per % reduction
        # Urban Canopy: -2.2 ppm per km² added
        # Industrial Shutdown: -14 ppm per curtailed facility
        # DAC Pods: -3.8 ppm per operational direct capture unit
        ind_impact = len(industrial_shutdown) * 14.0
        dac_impact = dac_units * 3.8
        total_reduction = (traffic_reduction * 0.45) + (green_increase * 2.2) + ind_impact + dac_impact
        
        projected = max(350.0, baseline - total_reduction)
        reduction_pct = ((baseline - projected) / baseline) * 100 if baseline > 0 else 0
        
        # Diurnal dispersion curve over duration
        hourly = []
        for i in range(duration):
            decay = min(1.0, (i + 1) / 8.0) # ramps up over first 8 hours
            diurnal = 5.0 * np.sin((i - 6) * np.pi / 12) # daily flux
            val = max(350.0, baseline + diurnal - (total_reduction * decay))
            hourly.append(round(val, 2))
        
        result = {
            "scenario_name": scenario_name,
            "baseline_co2": round(baseline, 2),
            "projected_co2": round(projected, 2),
            "reduction_pct": round(reduction_pct, 2),
            "total_reduction_ppm": round(baseline - projected, 2),
            "hourly_forecast": hourly,
            "breakdown": {
                "traffic_reduction_ppm": round(traffic_reduction * 0.45, 2),
                "green_canopy_ppm": round(green_increase * 2.2, 2),
                "industrial_curtailment_ppm": round(ind_impact, 2),
                "dac_capture_ppm": round(dac_impact, 2)
            }
        }
        
        # Persist to database
        session = self.Session()
        try:
            sim_record = SimulationResults(
                ScenarioName=scenario_name,
                SimulatedCO2=round(projected, 2),
                Parameters=params
            )
            session.add(sim_record)
            session.commit()
        except Exception as e:
            logger.error(f"Error persisting simulation: {e}")
            session.rollback()
        finally:
            session.close()
        
        return result

    def get_hotspots(self):
        if not self.state:
            self.sync_state()
        with self.lock:
            ranked = sorted(self.state.items(), key=lambda x: x[1]['latest_co2'], reverse=True)
            return ranked[:5]

    def optimize_capture_placement(self):
        if not self.state:
            self.sync_state()
        with self.lock:
            recommendations = []
            for sid, data in self.state.items():
                meta = self.METADATA_DEFAULTS.get(sid, {
                    "pop": 8500, "acc": 0.85, "cost": "Tier 2 ($$)", 
                    "tag": "Metropolitan Grid Node", 
                    "action": "Deploy Direct Air Capture & Urban Forestry"
                })
                intensity = data['latest_co2']
                pop = meta["pop"]
                acc = meta["acc"]
                score = round((intensity / 100.0) * (pop / 1000.0) * acc, 1)
                
                recommendations.append({
                    "sensor_id": sid,
                    "location": data['location'],
                    "co2_ppm": intensity,
                    "population_density": pop,
                    "accessibility_score": acc,
                    "priority_score": score,
                    "capex_tier": meta["cost"],
                    "category": meta["tag"],
                    "recommended_action": meta["action"]
                })
            
            recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
            return recommendations

twin_engine = TwinEngine()
