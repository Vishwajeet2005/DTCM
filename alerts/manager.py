import logging
import datetime
from sqlalchemy.orm import Session
from db.models import Alerts, EnvironmentalData, SensorData
from config import config

logger = logging.getLogger(__name__)

class AlertManager:
    @staticmethod
    def evaluate(session: Session, data_row: EnvironmentalData):
        co2 = data_row.CO2Level
        
        # Check thresholds
        alert_type = None
        message = ""
        
        if co2 > config.CO2_CRITICAL_THRESHOLD:
            alert_type = "Critical"
            message = f"CO2 levels critically high: {co2:.1f} ppm"
        elif co2 > config.CO2_WARNING_THRESHOLD:
            alert_type = "Warning"
            message = f"CO2 levels elevated: {co2:.1f} ppm"
            
        if alert_type:
            # Check for existing active alert for this sensor within last 30 minutes
            thirty_mins_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
            
            existing = session.query(Alerts).join(EnvironmentalData).filter(
                EnvironmentalData.SensorID == data_row.SensorID,
                Alerts.Status == 'Active',
                Alerts.AlertTime >= thirty_mins_ago
            ).first()
            
            if not existing:
                new_alert = Alerts(
                    DataID=data_row.DataID,
                    AlertType=alert_type,
                    Message=message,
                    Status='Active'
                )
                session.add(new_alert)
                logger.warning(f"New Alert Generated: {alert_type} for Sensor {data_row.SensorID}")
                
                # Here we could push SSE event or send email
                # For SSE, we can use a message broker (Redis) or just a shared in-memory queue if single-process.
        
        # Auto-resolve
        # If CO2 drops below warning threshold for 3 consecutive readings, resolve active alerts
        if co2 <= config.CO2_WARNING_THRESHOLD:
            active_alerts = session.query(Alerts).join(EnvironmentalData).filter(
                EnvironmentalData.SensorID == data_row.SensorID,
                Alerts.Status == 'Active'
            ).all()
            
            if active_alerts:
                # Check last 3 readings for this sensor
                last_3 = session.query(EnvironmentalData).filter(
                    EnvironmentalData.SensorID == data_row.SensorID
                ).order_by(EnvironmentalData.Timestamp.desc()).limit(3).all()
                
                if len(last_3) == 3 and all(r.CO2Level <= config.CO2_WARNING_THRESHOLD for r in last_3):
                    for alert in active_alerts:
                        alert.Status = 'Resolved'
                        alert.Message += " (Auto-resolved)"
                    logger.info(f"Auto-resolved alerts for Sensor {data_row.SensorID}")

alert_manager = AlertManager()
