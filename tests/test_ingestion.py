"""
Tests for data ingestion and alert generation utilities.
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from ingestion import (
    generate_synthetic_reading,
    import_csv_data,
    process_reading
)
from models import SensorData, Alert

def test_synthetic_reading_format():
    """Test that synthetic readings contain required fields."""
    reading = generate_synthetic_reading('Zone A')
    
    assert 'zone_id' in reading
    assert reading['zone_id'] == 'Zone A'
    assert 'co2_level' in reading
    assert 'temperature' in reading
    assert 'humidity' in reading
    assert 'timestamp' in reading

def test_synthetic_co2_range():
    """Test that synthetic CO2 readings fall within expected realistic ranges."""
    readings = [generate_synthetic_reading('Zone B')['co2_level'] for _ in range(100)]
    
    for co2 in readings:
        assert 300 <= co2 <= 2000, "CO2 reading out of bounds"

def test_csv_import_valid(tmp_path):
    """Test importing a valid CSV file."""
    csv_file = tmp_path / "valid_data.csv"
    df = pd.DataFrame({
        'timestamp': ['2023-10-01T12:00:00Z', '2023-10-01T12:05:00Z'],
        'zone_id': ['Zone A', 'Zone B'],
        'co2_level': [410.5, 460.0],
        'temperature': [22.1, 23.0],
        'humidity': [45.0, 50.0]
    })
    df.to_csv(csv_file, index=False)
    
    # Mock the database session
    mock_db = MagicMock()
    result = import_csv_data(str(csv_file), db_session=mock_db)
    
    assert result['status'] == 'success'
    assert result['records_imported'] == 2
    assert mock_db.add_all.called
    assert mock_db.commit.called

def test_csv_import_missing_required_column(tmp_path):
    """Test importing a CSV missing a required column (e.g., co2_level)."""
    csv_file = tmp_path / "missing_col.csv"
    df = pd.DataFrame({
        'timestamp': ['2023-10-01T12:00:00Z'],
        'zone_id': ['Zone A'],
        # 'co2_level' is missing
        'temperature': [22.1],
    })
    df.to_csv(csv_file, index=False)
    
    mock_db = MagicMock()
    with pytest.raises(ValueError) as excinfo:
        import_csv_data(str(csv_file), db_session=mock_db)
    
    assert "Missing required columns" in str(excinfo.value)
    assert not mock_db.add_all.called

def test_csv_import_bad_data(tmp_path):
    """Test importing a CSV with invalid data types."""
    csv_file = tmp_path / "bad_data.csv"
    df = pd.DataFrame({
        'timestamp': ['2023-10-01T12:00:00Z'],
        'zone_id': ['Zone A'],
        'co2_level': ['not_a_number'],
        'temperature': [22.1],
        'humidity': [45.0]
    })
    df.to_csv(csv_file, index=False)
    
    mock_db = MagicMock()
    result = import_csv_data(str(csv_file), db_session=mock_db)
    
    # Should either skip the row or fail gracefully depending on implementation
    assert result['records_imported'] == 0
    assert result['errors'] > 0

@patch('dtcm.ingestion.create_alert')
def test_insert_reading_creates_alert(mock_create_alert):
    """Test that inserting a reading with high CO2 triggers an alert."""
    mock_db = MagicMock()
    
    # Normal reading
    process_reading({
        'zone_id': 'Zone A',
        'co2_level': 400.0,
        'temperature': 22.0,
        'humidity': 50.0
    }, db_session=mock_db)
    mock_create_alert.assert_not_called()
    
    # Warning reading (>450)
    process_reading({
        'zone_id': 'Zone A',
        'co2_level': 460.0,
        'temperature': 22.0,
        'humidity': 50.0
    }, db_session=mock_db)
    mock_create_alert.assert_called_with(mock_db, 'Zone A', 460.0, 'Warning')
    
    mock_create_alert.reset_mock()
    
    # Critical reading (>500)
    process_reading({
        'zone_id': 'Zone B',
        'co2_level': 550.0,
        'temperature': 22.0,
        'humidity': 50.0
    }, db_session=mock_db)
    mock_create_alert.assert_called_with(mock_db, 'Zone B', 550.0, 'Critical')

