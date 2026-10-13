from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
from app_db import db

Base = declarative_base()

class SensorData(Base):
    __tablename__ = 'SensorData'
    SensorID = Column(Integer, primary_key=True, autoincrement=True)
    Location = Column(String(255), nullable=False)
    Type = Column(String(100), nullable=False) # e.g. 'CO2', 'AQI', 'Traffic'
    InstallationDate = Column(DateTime)
    Status = Column(String(50), default='Active')

    def __init__(self, **kwargs):
        key_map = {
            'sensor_id': 'SensorID', 'location': 'Location', 'type': 'Type',
            'installation_date': 'InstallationDate', 'status': 'Status'
        }
        mapped = {key_map.get(k.lower(), k): v for k, v in kwargs.items()}
        super().__init__(**mapped)

    @property
    def sensor_id(self):
        return self.SensorID

    @property
    def location(self):
        return self.Location

class EnvironmentalData(Base):
    __tablename__ = 'EnvironmentalData'
    DataID = Column(Integer, primary_key=True, autoincrement=True)
    SensorID = Column(Integer, ForeignKey('SensorData.SensorID'))
    CO2Level = Column(Float, nullable=False) # ppm
    Temperature = Column(Float) # Celsius
    Humidity = Column(Float) # %
    PM2S = Column(Float) # µg/m³
    AQI = Column(Float)
    Timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    data_gap = Column(Boolean, default=False)
    
    sensor = relationship("SensorData")

    def __init__(self, **kwargs):
        key_map = {
            'data_id': 'DataID', 'sensor_id': 'SensorID', 'co2_level': 'CO2Level',
            'temperature': 'Temperature', 'humidity': 'Humidity',
            'pm25': 'PM2S', 'pm2s': 'PM2S', 'aqi': 'AQI', 'timestamp': 'Timestamp',
            'data_gap': 'data_gap'
        }
        mapped = {key_map.get(k.lower(), k): v for k, v in kwargs.items()}
        super().__init__(**mapped)

    @property
    def data_id(self):
        return self.DataID

    @property
    def sensor_id(self):
        return self.SensorID

    @property
    def co2_level(self):
        return self.CO2Level

class Users(Base):
    __tablename__ = 'Users'
    UserID = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(255))
    Email = Column(String(255), unique=True, nullable=False)
    Role = Column(Enum('environmental_authority','administrator','researcher','general'), nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        key_map = {
            'user_id': 'UserID', 'name': 'Name', 'email': 'Email',
            'role': 'Role', 'password_hash': 'PasswordHash', 'created_at': 'CreatedAt'
        }
        mapped = {key_map.get(k.lower(), k): v for k, v in kwargs.items()}
        super().__init__(**mapped)

class PredictionResults(Base):
    __tablename__ = 'PredictionResults'
    PredictionID = Column(Integer, primary_key=True, autoincrement=True)
    DataID = Column(Integer, ForeignKey('EnvironmentalData.DataID'))
    PredictedCO2 = Column(Float, nullable=False)
    ModelUsed = Column(String(100))
    ConfidenceLow = Column(Float)
    ConfidenceHigh = Column(Float)
    PredictionTime = Column(DateTime, default=datetime.datetime.utcnow)
    
    data = relationship("EnvironmentalData")

class SimulationResults(Base):
    __tablename__ = 'SimulationResults'
    SimID = Column(Integer, primary_key=True, autoincrement=True)
    ScenarioName = Column(String(255))
    SimulatedCO2 = Column(Float)
    Parameters = Column(JSON)
    SimTime = Column(DateTime, default=datetime.datetime.utcnow)

class Alerts(Base):
    __tablename__ = 'Alerts'
    AlertID = Column(Integer, primary_key=True, autoincrement=True)
    DataID = Column(Integer, ForeignKey('EnvironmentalData.DataID'))
    AlertType = Column(String(100))
    Message = Column(String(500))
    AlertTime = Column(DateTime, default=datetime.datetime.utcnow)
    Status = Column(Enum('Active','Acknowledged','Resolved'), default='Active')
    
    data = relationship("EnvironmentalData")
