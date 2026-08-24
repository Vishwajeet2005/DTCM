import logging
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional
import queue

class AlertManager:
    """Evaluates sensor readings, creates alerts, auto-resolves, pushes SSE events."""
    
    def __init__(self):
        self._consecutive_below = {}
        self.listeners = []
        self.logger = logging.getLogger('AlertManager')
    
    def listen(self):
        """Register a new SSE client listener."""
        q = queue.Queue(maxsize=20)
        self.listeners.append(q)
        return q

    def get_threshold(self, sensor_id: int, session) -> tuple[float, float]:
        """Returns (warning_threshold, critical_threshold) for a sensor's zone."""
        try:
            # Try to import Thresholds model dynamically to avoid circular dependencies
            from db.models import Thresholds
            threshold = session.query(Thresholds).filter_by(sensor_id=sensor_id).first()
            if threshold:
                # Ensure we handle possible string or numeric types safely
                return float(threshold.warning_level), float(threshold.critical_level)
        except ImportError:
            self.logger.warning("models module not found, using default thresholds")
        except Exception as e:
            self.logger.error(f"Error fetching threshold for sensor {sensor_id}: {e}")
            
        # Defaults: Warning=450ppm, Critical=500ppm
        return 450.0, 500.0
    
    def evaluate(self, data_row, session):
        """Evaluate a data row to trigger or resolve alerts."""
        try:
            sensor_id = data_row.sensor_id
            co2_level = float(data_row.co2_level)
            data_id = data_row.id
        except AttributeError:
            self.logger.error("data_row missing required attributes (sensor_id, co2_level, id)")
            return
            
        warning_th, critical_th = self.get_threshold(sensor_id, session)
        
        alert_type = None
        if co2_level >= critical_th:
            alert_type = 'critical'
        elif co2_level >= warning_th:
            alert_type = 'warning'
            
        if alert_type:
            # Reset consecutive normal readings counter
            self._consecutive_below[sensor_id] = 0
            
            # Create alert if not already active
            if not self.check_deduplication(sensor_id, session):
                self.create_alert(sensor_id, data_id, alert_type, co2_level, session)
        else:
            # Increment consecutive normal readings
            count = self._consecutive_below.get(sensor_id, 0) + 1
            self._consecutive_below[sensor_id] = count
            
            # After 3 consecutive normal readings, auto-resolve active alerts
            if count >= 3:
                self.auto_resolve(sensor_id, session)
                self._consecutive_below[sensor_id] = 0

    def create_alert(self, sensor_id: int, data_id: Optional[int], alert_type: str, co2_level: float, session):
        """Create a new alert and push SSE."""
        try:
            from db.models import Alerts
            new_alert = Alerts(
                sensor_id=sensor_id,
                data_id=data_id,
                alert_type=alert_type,
                co2_level=co2_level,
                timestamp=datetime.utcnow(),
                status='active',
                description=f"CO2 level {co2_level} ppm exceeded {alert_type} threshold."
            )
            session.add(new_alert)
            session.commit()
            
            alert_dict = {
                "id": new_alert.id,
                "sensor_id": sensor_id,
                "alert_type": alert_type,
                "co2_level": co2_level,
                "timestamp": new_alert.timestamp.isoformat(),
                "status": "active"
            }
            self.push_sse_alert(alert_dict)
            
            if alert_type == 'critical':
                self.send_email_alert(alert_dict)
                
            self.logger.info(f"Alert created: Sensor {sensor_id}, Type {alert_type}, CO2 {co2_level}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to create alert: {e}")
    
    def push_sse_alert(self, alert_dict: dict):
        """Push JSON alert data to all connected SSE clients."""
        msg = f"data: {json.dumps(alert_dict)}\n\n"
        # Iterate in reverse so we can safely remove dead queues
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                # If a client's queue is full, they are likely disconnected/stuck
                del self.listeners[i]
    
    def auto_resolve(self, sensor_id: int, session):
        """Resolve active alerts for a sensor."""
        try:
            from db.models import Alerts
            active_alerts = session.query(Alerts).filter_by(
                sensor_id=sensor_id, 
                status='active'
            ).all()
            
            resolved_count = 0
            for alert in active_alerts:
                alert.status = 'resolved'
                alert.resolved_at = datetime.utcnow()
                resolved_count += 1
                
                alert_dict = {
                    "id": alert.id,
                    "sensor_id": sensor_id,
                    "alert_type": alert.alert_type,
                    "status": "resolved",
                    "resolved_at": alert.resolved_at.isoformat()
                }
                self.push_sse_alert(alert_dict)
                
            if resolved_count > 0:
                session.commit()
                self.logger.info(f"Auto-resolved {resolved_count} alert(s) for sensor {sensor_id}.")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to auto-resolve alerts: {e}")
    
    def send_email_alert(self, alert: dict):
        """Mock/Basic email sending for critical alerts."""
        import os
        smtp_server = os.getenv("SMTP_SERVER")
        if not smtp_server:
            self.logger.debug(f"Email alert suppressed (SMTP_SERVER not set) for sensor {alert.get('sensor_id')}")
            return
            
        try:
            smtp_port = int(os.getenv("SMTP_PORT", 1025))
            sender = os.getenv("MAIL_DEFAULT_SENDER", "alerts@dtcm.local")
            recipient = os.getenv("ADMIN_EMAIL", "admin@dtcm.local")
            
            msg = MIMEText(f"Critical Alert on Sensor {alert['sensor_id']}! CO2 level reached {alert['co2_level']} ppm.")
            msg['Subject'] = f"DTCM Critical Alert - Sensor {alert['sensor_id']}"
            msg['From'] = sender
            msg['To'] = recipient
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.send_message(msg)
            self.logger.info(f"Email alert sent to {recipient} for sensor {alert['sensor_id']}.")
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    def check_deduplication(self, sensor_id: int, session) -> bool:
        """Check if an active alert already exists for the sensor."""
        try:
            from db.models import Alerts
            active = session.query(Alerts).filter_by(
                sensor_id=sensor_id, 
                status='active'
            ).first()
            return active is not None
        except Exception as e:
            self.logger.error(f"Error checking deduplication: {e}")
            return False

alert_manager = AlertManager()

