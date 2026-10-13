import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app_db import db

from config import TestingConfig
from db.models import Base, Users, SensorData
import bcrypt

@pytest.fixture
def app():
    app = create_app(TestingConfig)

    with app.app_context():
        Base.metadata.create_all(db.engine)
        
        # Insert test data
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt(12))
        admin = Users(Email="admin@test.com", PasswordHash=hashed.decode('utf-8'), Role="administrator")
        db.session.add(admin)
        
        sensor = SensorData(SensorID=1, Location="Test Zone", Type="CO2")
        db.session.add(sensor)
        
        db.session.commit()
        yield app
        db.session.remove()
        Base.metadata.drop_all(db.engine)

@pytest.fixture
def client(app):
    return app.test_client()

def test_live_data(client):
    response = client.get('/api/data/live')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_login_and_auth_route(client):
    # Test valid login
    res = client.post('/api/auth/login', json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    assert res.status_code == 200
    assert 'access_token' in res.json
    
    token = res.json['access_token']
    
    # Test protected route without token (401)
    res_no_auth = client.post('/api/predict/short-term', json={"sensor_id": 1})
    assert res_no_auth.status_code == 401
    
    # Test protected route with token
    res_auth = client.post('/api/predict/short-term', json={"sensor_id": 1}, headers={
        "Authorization": f"Bearer {token}"
    })
    # Will be 404 because no environmental data for sensor 1 yet, but not 401
    assert res_auth.status_code == 404

def test_login_invalid(client):
    res = client.post('/api/auth/login', json={
        "email": "wrong@test.com",
        "password": "wrong"
    })
    assert res.status_code == 401

def test_simulation(client):
    res = client.post('/api/twin/simulate', json={
        "traffic_reduction_pct": 20
    })
    assert res.status_code == 200
    assert "projected_co2" in res.json
