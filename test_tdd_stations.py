import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from app import schemas, models

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    """Fixture untuk mock database session."""
    with patch('main.repository') as mock_repo:
        yield mock_repo

def test_search_stations_by_operator_found(mock_db_session: MagicMock):
    mock_station_data = [
        models.Station(
            station_id=1,
            station_operator="Operator A",
            location=models.Location(latitude=1.0, longitude=1.0, address="Jalan A"),
            connector_list=[]
        )
    ]
    mock_db_session.search_stations_by_operator.return_value = mock_station_data
    response = client.get("/stations/search?operator=Operator A")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["station_operator"] == "Operator A"