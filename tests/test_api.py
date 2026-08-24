"""
Tests for API endpoints in DTCM.
"""
import pytest
import json
import io

def test_register_user_success(client):
    """Test successful user registration."""
    response = client.post('/api/auth/register', json={
        'email': 'newuser@example.com',
        'password': 'password123',
        'role': 'general'
    })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'message' in data

def test_register_duplicate_email(client):
    """Test user registration with an already existing email."""
    # First registration
    client.post('/api/auth/register', json={
        'email': 'duplicate@example.com',
        'password': 'password123',
        'role': 'general'
    })
    
    # Second registration
    response = client.post('/api/auth/register', json={
        'email': 'duplicate@example.com',
        'password': 'password123',
        'role': 'general'
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_login_success(client):
    """Test successful login returns a JWT."""
    # Register first
    client.post('/api/auth/register', json={
        'email': 'loginuser@example.com',
        'password': 'password123',
        'role': 'general'
    })
    
    response = client.post('/api/auth/login', json={
        'email': 'loginuser@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data

def test_login_wrong_password(client):
    """Test login fails with incorrect password."""
    client.post('/api/auth/register', json={
        'email': 'login2@example.com',
        'password': 'password123',
        'role': 'general'
    })
    
    response = client.post('/api/auth/login', json={
        'email': 'login2@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401

def test_get_live_data_authenticated(client, auth_headers):
    """Test fetching live sensor data when authenticated."""
    response = client.get('/api/sensors/live', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_get_live_data_unauthenticated(client):
    """Test fetching live sensor data when not authenticated."""
    response = client.get('/api/sensors/live')
    assert response.status_code == 401

def test_get_history_with_params(client, auth_headers):
    """Test fetching historical data with query parameters."""
    response = client.get('/api/sensors/history?zone_id=Zone A&limit=10', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    if len(data) > 0:
        assert data[0]['zone_id'] == 'Zone A'

def test_get_alerts_active(client, auth_headers):
    """Test fetching active alerts."""
    response = client.get('/api/alerts?status=active', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_acknowledge_alert_unauthorized(client):
    """Test acknowledging an alert without authorization fails."""
    response = client.post('/api/alerts/1/acknowledge')
    assert response.status_code == 401

def test_get_twin_state(client, auth_headers):
    """Test fetching the current digital twin state."""
    response = client.get('/api/twin/state', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'timestamp' in data
    assert 'zones' in data

def test_classify_zones(client, auth_headers):
    """Test the zone classification endpoint."""
    response = client.get('/api/ml/classify', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, dict)

def test_csv_import_unauthorized(client):
    """Test CSV import without authentication/correct role fails."""
    data = {'file': (io.BytesIO(b"timestamp,zone_id,co2_level\n2023-01-01,Zone A,400"), 'test.csv')}
    response = client.post('/api/ingestion/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 401

