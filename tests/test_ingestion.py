import pytest
from ingestion.collector import DataCollector
from app import create_app

def test_data_collector_init():
    app = create_app()
    with app.app_context():
        dc = DataCollector()
        assert dc.poll_interval == 60
        reading = dc.generate_synthetic_reading(1)
        assert 'co2_level' in reading
        assert 'temperature' in reading
