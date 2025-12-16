import pytest
from unittest.mock import patch, MagicMock
from app import service, models


@patch("app.service.repository")
def test_start_charging_success(mock_repo):
    mock_repo.get_user.return_value = MagicMock(id=1)
    mock_repo.get_active_session_by_user.return_value = None

    asset = MagicMock()
    asset.is_available = True
    asset.connector_port = MagicMock(max_power_supported=7.0)

    mock_repo.get_station_asset.return_value = asset
    mock_repo.create_charging_session.return_value = MagicMock(id=1)

    result = service.start_charging_session(1, 1)
    assert result.id == 1


@patch("app.service.repository")
def test_start_charging_user_not_found(mock_repo):
    mock_repo.get_user.return_value = None

    with pytest.raises(ValueError):
        service.start_charging_session(1, 1)


@patch("app.service.repository")
def test_stop_charging_success(mock_repo):
    session = MagicMock()
    session.charging_status = models.ChargingStatus.ONGOING
    session.start_time = service.datetime.utcnow()
    session.asset_id = 1

    asset = MagicMock()
    asset.connector_port = MagicMock(max_power_supported=7.0)

    mock_repo.get_charging_session.return_value = session
    mock_repo.get_station_asset.return_value = asset
    mock_repo.execute_stop_session_transaction.return_value = session

    result = service.stop_charging_session(1)
    assert result == session


@patch("app.service.repository")
def test_add_maintenance_log_success(mock_repo):
    mock_repo.get_station_asset.return_value = MagicMock()
    mock_repo.update_station_asset.return_value = True

    result = service.add_maintenance_log(1, "Error")
    assert result is True


@patch("app.service.repository")
def test_update_invoice_payment_valid(mock_repo):
    invoice = MagicMock()
    mock_repo.get_invoice.return_value = invoice
    mock_repo.update_invoice.return_value = invoice

    result = service.update_invoice_payment(
        invoice_id=1,
        status="Completed",
        method="cash"
    )

    assert result == invoice