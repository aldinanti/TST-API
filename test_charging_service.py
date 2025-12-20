import pytest
import asyncio
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from app import service, models, auth, repository,db
from app.schemas import (
    UserRegister, UserLogin, Token, TokenData,
    VehicleCreate, StationCreate, StationAssetCreate,
    ChargingSessionStart, InvoiceUpdatePayment,
    LocationBase, ConnectorPortBase, MaintenanceLogBase
)

# =====================================================
# SERVICE — START CHARGING SESSION
# =====================================================

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
def test_start_charging_active_session_exists(mock_repo):
    mock_repo.get_user.return_value = MagicMock()
    mock_repo.get_active_session_by_user.return_value = MagicMock()
    with pytest.raises(ValueError):
        service.start_charging_session(1, 1)


@patch("app.service.repository")
def test_start_charging_asset_not_available(mock_repo):
    mock_repo.get_user.return_value = MagicMock()
    mock_repo.get_active_session_by_user.return_value = None

    asset = MagicMock(is_available=False)
    mock_repo.get_station_asset.return_value = asset

    with pytest.raises(ValueError):
        service.start_charging_session(1, 1)

# =====================================================
# SERVICE — CALCULATION
# =====================================================

def test_calculate_session_details_manual_kwh():
    session = MagicMock(
        charging_status=models.ChargingStatus.ONGOING,
        start_time=datetime.utcnow()
    )
    asset = MagicMock()
    asset.connector_port = MagicMock(max_power_supported=7)

    result = service._calculate_session_details(session, asset, manual_kwh=10)
    assert result["total_kwh"] == 10


def test_calculate_billing_positive():
    result = service._calculate_billing(5, 30)
    assert result["billing_total"] > result["total_cost"]

# =====================================================
# SERVICE — STOP SESSION
# =====================================================

@patch("app.service.repository")
def test_stop_charging_success(mock_repo):
    session = MagicMock(
        charging_status=models.ChargingStatus.ONGOING,
        start_time=datetime.utcnow(),
        asset_id=1
    )
    asset = MagicMock()
    asset.connector_port = MagicMock(max_power_supported=7)

    mock_repo.get_charging_session.return_value = session
    mock_repo.get_station_asset.return_value = asset
    mock_repo.execute_stop_session_transaction.return_value = session

    result = service.stop_charging_session(1)
    assert result == session

# =====================================================
# SERVICE — MAINTENANCE
# =====================================================

@patch("app.service.repository")
def test_add_maintenance_log_success(mock_repo):
    asset = MagicMock()
    mock_repo.get_station_asset.return_value = asset
    mock_repo.update_station_asset.return_value = asset

    result = service.add_maintenance_log(1, "error")
    assert result.is_available is False

@patch("app.service.repository")
def test_add_maintenance_log_asset_not_found(mock_repo):
    mock_repo.get_station_asset.return_value = None 

    with pytest.raises(ValueError, match="Asset tidak ditemukan"):
        service.add_maintenance_log(asset_id=999, error_log="error")

# =====================================================
# SERVICE — INVOICE
# =====================================================

@patch("app.service.repository")
def test_update_invoice_payment_valid(mock_repo):
    invoice = MagicMock()
    mock_repo.get_invoice.return_value = invoice
    mock_repo.update_invoice.return_value = invoice

    result = service.update_invoice_payment(1, "Completed", "cash")
    assert result == invoice

@patch("app.service.repository")
def test_update_invoice_payment_invoice_not_found(mock_repo):
    mock_repo.get_invoice.return_value = None
    with pytest.raises(ValueError):
        service.update_invoice_payment(1, "Completed", "cash")

@patch("app.service.repository")
def test_update_invoice_payment_invalid_status(mock_repo):
    invoice = MagicMock()
    mock_repo.get_invoice.return_value = invoice

    with pytest.raises(ValueError, match="Status pembayaran tidak valid"):
        service.update_invoice_payment(
            invoice_id=1,
            status="SALAH_TOTAL",
            method="cash"
        )

@patch("app.service.repository")
def test_update_invoice_payment_valid_enum(mock_repo):
    invoice = MagicMock()
    mock_repo.get_invoice.return_value = invoice
    mock_repo.update_invoice.return_value = invoice

    result = service.update_invoice_payment(
        invoice_id=1,
        status=models.PaymentStatus.COMPLETED.value,
        method="cash"
    )

    assert result == invoice
# =====================================================
# AUTH — PASSWORD & TOKEN
# =====================================================

def test_password_hash_and_verify():
    password = "secret123"
    hashed = auth.get_password_hash(password)
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = auth.create_access_token({"sub": "1", "email": "test@mail.com"})
    payload = auth.decode_access_token(token)
    assert payload["sub"] == "1"


def test_decode_invalid_token():
    with pytest.raises(HTTPException) as exc:
        auth.decode_access_token("invalid.token.here")

    assert exc.value.status_code == 401

def test_create_token_with_custom_expiry():
    token = auth.create_access_token(
        {"sub": "1"},
        expires_delta=timedelta(minutes=5)
    )
    payload = auth.decode_access_token(token)
    assert payload["sub"] == "1"

@patch("app.auth.decode_access_token")
def test_get_current_user(mock_decode):
    mock_decode.return_value = {"sub": "1", "email": "a@b.com"}
    credentials = MagicMock(credentials="token")

    result = asyncio.run(auth.get_current_user(credentials))
    assert result["user_id"] == 1

# =====================================================
# SCHEMAS — VALIDATION
# =====================================================

def test_user_register_schema():
    data = UserRegister(
        name="Test",
        email="test@mail.com",
        password="123"
    )
    assert data.email == "test@mail.com"


def test_vehicle_schema():
    vehicle = VehicleCreate(
        nomor_plat="B1234CD",
        battery_capacity=40,
        connector_port=ConnectorPortBase(
            standard_name="Type2",
            max_power_supported=7
        )
    )
    assert vehicle.battery_capacity == 40


def test_station_schema():
    station = StationCreate(
        station_operator="PLN",
        location=LocationBase(
            latitude=1.2,
            longitude=3.4,
            address="Jakarta"
        ),
        connector_list=["Type2"]
    )
    assert station.location.address == "Jakarta"

@patch("app.service.repository")
def test_get_station_details_station_not_found(mock_repo):
    mock_repo.get_station.return_value = None

    with pytest.raises(ValueError, match="Station tidak ditemukan"):
        service.get_station_details(999)

def test_maintenance_schema_optional():
    log = MaintenanceLogBase(
        error_log="error",
        date_time=datetime.utcnow()
    )
    assert log.error_log == "error"

# =====================================================
# REPOSITORY — BASIC CRUD (MOCKED)
# =====================================================

@patch("app.repository.get_db_session")
def test_repository_create_user(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s

    user = MagicMock()
    result = repository.create_user(user)

    mock_s.add.assert_called()
    mock_s.commit.assert_called()
    assert result == user


@patch("app.repository.get_db_session")
def test_repository_get_user(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s

    mock_s.get.return_value = "USER"
    result = repository.get_user(1)
    assert result == "USER"

# =====================================================
# SERVICE — EXTRA FAILURE PATHS
# =====================================================

@patch("app.service.repository")
def test_start_charging_asset_not_found(mock_repo):
    mock_repo.get_user.return_value = MagicMock()
    mock_repo.get_active_session_by_user.return_value = None
    mock_repo.get_station_asset.return_value = None 

    with pytest.raises(ValueError, match="Asset tidak ditemukan"):
        service.start_charging_session(user_id=1, asset_id=999)

def test_calculate_session_details_session_none():
    with pytest.raises(ValueError):
        service._calculate_session_details(None, None)

def test_calculate_session_details_not_ongoing():
    session = MagicMock()
    session.charging_status = models.ChargingStatus.STOPPED

    with pytest.raises(ValueError):
        service._calculate_session_details(session, None)


@patch("app.service.repository")
def test_stop_charging_session_not_found(mock_repo):
    mock_repo.get_charging_session.return_value = None
    with pytest.raises(ValueError):
        service.stop_charging_session(1)

@patch("app.service.repository")
def test_stop_charging_asset_not_found(mock_repo):
    session = MagicMock(
        charging_status=models.ChargingStatus.ONGOING,
        asset_id=1
    )
    mock_repo.get_charging_session.return_value = session
    mock_repo.get_station_asset.return_value = None

    with pytest.raises(ValueError):
        service.stop_charging_session(1)

@patch("app.service.repository")
def test_get_station_details_station_not_found(mock_repo):
    mock_repo.get_station.return_value = None

    with pytest.raises(ValueError, match="Station tidak ditemukan"):
        service.get_station_details(999)

@patch("app.service.repository")
def test_get_station_details_success(mock_repo):
    station = MagicMock()
    assets = [MagicMock(), MagicMock()]

    mock_repo.get_station.return_value = station
    mock_repo.get_station_assets_by_station.return_value = assets

    result = service.get_station_details(1)

    assert result == station
    assert result.station_assets == assets
# =====================================================
# AUTH — EDGE CASES
# =====================================================

def test_create_token_without_sub():
    token = auth.create_access_token({"email": "a@b.com"})
    payload = auth.decode_access_token(token)
    assert "email" in payload


def test_expired_token():
    expired = auth.create_access_token(
        {"sub": "1"},
        expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(Exception):
        auth.decode_access_token(expired)


@patch("app.auth.decode_access_token")
def test_get_current_user_no_sub(mock_decode):
    mock_decode.return_value = {"email": "x@y.com"}
    credentials = MagicMock(credentials="token")

    with pytest.raises(Exception):
        asyncio.run(auth.get_current_user(credentials))

# =====================================================
# REPOSITORY — LIST & SEARCH PATHS
# =====================================================

@patch("app.repository.get_db_session")
def test_list_users(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s
    mock_s.exec.return_value.all.return_value = []

    result = repository.list_users()
    assert result == []


@patch("app.repository.get_db_session")
def test_search_station_by_operator(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s
    mock_s.exec.return_value.all.return_value = ["station"]

    result = repository.search_stations_by_operator("PLN")
    assert result == ["station"]


@patch("app.repository.get_db_session")
def test_get_available_station_assets_all(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s
    mock_s.exec.return_value.all.return_value = ["asset"]

    result = repository.get_available_station_assets()
    assert result == ["asset"]


@patch("app.repository.get_db_session")
def test_get_available_station_assets_by_station(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s
    mock_s.exec.return_value.all.return_value = ["asset"]

    result = repository.get_available_station_assets(1)
    assert result == ["asset"]


@patch("app.repository.get_db_session")
def test_get_active_session_by_user(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s
    mock_s.exec.return_value.first.return_value = "session"

    result = repository.get_active_session_by_user(1)
    assert result == "session"

# =====================================================
# REPOSITORY — TRANSACTION BRANCH
# =====================================================

@patch("app.repository.get_db_session")
def test_execute_stop_session_transaction(mock_session):
    mock_s = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_s

    session = MagicMock(session_id=1, user_id=1)
    asset = MagicMock()
    tariff = MagicMock()

    details = {
        "end_time": datetime.utcnow(),
        "duration_minutes": 30,
        "total_kwh": 5,
        "total_cost": 100,
        "billing_total": 110
    }

    result = repository.execute_stop_session_transaction(
        session, asset, details, tariff
    )

    mock_s.commit.assert_called()
    assert result == session

# =====================================================
# custom_json_serializer
# =====================================================

def test_custom_json_serializer_datetime():
    now = datetime(2025, 1, 1, 10, 0, 0)
    result = db.custom_json_serializer(now)
    assert result == now.isoformat()


def test_custom_json_serializer_model_dump():
    class Dummy:
        def model_dump(self, mode="json"):
            return {"a": 1}

    obj = Dummy()
    result = db.custom_json_serializer(obj)
    assert result == {"a": 1}


def test_custom_json_serializer_dict_fallback():
    class Dummy:
        def dict(self):
            return {"b": 2}

    obj = Dummy()
    result = db.custom_json_serializer(obj)
    assert result == {"b": 2}


def test_custom_json_serializer_unsupported_type():
    with pytest.raises(TypeError):
        db.custom_json_serializer(set([1, 2, 3]))


# =====================================================
# dumps
# =====================================================

def test_dumps_with_datetime():
    data = {
        "time": datetime(2025, 1, 1, 10, 0, 0)
    }

    json_str = db.dumps(data)
    parsed = json.loads(json_str)

    assert "time" in parsed
    assert isinstance(parsed["time"], str)


# =====================================================
# init_db
# =====================================================

@patch("app.db.SQLModel.metadata.create_all")
def test_init_db(mock_create_all):
    db.init_db()
    mock_create_all.assert_called_once_with(db.engine)


# =====================================================
# get_session
# =====================================================

@patch("app.db.Session")
def test_get_session(mock_session):
    session = MagicMock()
    mock_session.return_value = session

    result = db.get_session()
    mock_session.assert_called_once_with(db.engine)
    assert result == session

# =====================================================
# Helper: Mock Session Context Manager
# =====================================================

class MockSession:
    def __init__(self):
        self.add = MagicMock()
        self.commit = MagicMock()
        self.refresh = MagicMock()
        self.get = MagicMock()
        self.exec = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def mock_session():
    return MockSession()


# =====================================================
# _save
# =====================================================

@patch("app.repository.get_db_session")
def test_save(mock_get_session):
    session = mock_session()
    mock_get_session.return_value = session

    obj = MagicMock()
    result = repository._save(obj)

    session.add.assert_called_once_with(obj)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(obj)
    assert result == obj


# =====================================================
# USER
# =====================================================

@patch("app.repository.get_db_session")
def test_create_and_get_user(mock_get_session):
    session = mock_session()
    user = MagicMock()
    session.get.return_value = user
    mock_get_session.return_value = session

    repository.create_user(user)
    result = repository.get_user(1)

    assert result == user


@patch("app.repository.get_db_session")
def test_get_user_by_email(mock_get_session):
    session = mock_session()
    session.exec.return_value.first.return_value = MagicMock()
    mock_get_session.return_value = session

    result = repository.get_user_by_email("test@mail.com")
    assert result is not None


@patch("app.repository.get_db_session")
def test_list_users(mock_get_session):
    session = mock_session()
    session.exec.return_value.all.return_value = []
    mock_get_session.return_value = session

    result = repository.list_users()
    assert result == []


# =====================================================
# VEHICLE
# =====================================================

@patch("app.repository.get_db_session")
def test_vehicle_functions(mock_get_session):
    session = mock_session()
    vehicle = MagicMock()
    session.get.return_value = vehicle
    session.exec.return_value.first.return_value = vehicle
    session.exec.return_value.all.return_value = [vehicle]
    mock_get_session.return_value = session

    repository.create_vehicle(vehicle)
    assert repository.get_vehicle(1) == vehicle
    assert repository.get_vehicle_by_plate("B1234") == vehicle
    assert repository.get_vehicles_by_user(1) == [vehicle]


# =====================================================
# STATION
# =====================================================

@patch("app.repository.get_db_session")
def test_station_functions(mock_get_session):
    session = mock_session()
    station = MagicMock()
    session.get.return_value = station
    session.exec.return_value.all.return_value = [station]
    mock_get_session.return_value = session

    repository.create_station(station)
    assert repository.get_station(1) == station
    assert repository.list_stations() == [station]
    assert repository.search_stations_by_operator("PLN") == [station]


# =====================================================
# STATION ASSET
# =====================================================

@patch("app.repository.get_db_session")
def test_station_asset_functions(mock_get_session):
    session = mock_session()
    asset = MagicMock()
    session.get.return_value = asset
    session.exec.return_value.all.return_value = [asset]
    mock_get_session.return_value = session

    repository.create_station_asset(asset)
    repository.update_station_asset(asset)
    assert repository.get_station_asset(1) == asset
    assert repository.get_station_assets_by_station(1) == [asset]
    assert repository.get_available_station_assets() == [asset]
    assert repository.get_available_station_assets(1) == [asset]


# =====================================================
# CHARGING SESSION
# =====================================================

@patch("app.repository.get_db_session")
def test_charging_session_functions(mock_get_session):
    session = mock_session()
    charging_session = MagicMock()
    session.get.return_value = charging_session
    session.exec.return_value.all.return_value = [charging_session]
    session.exec.return_value.first.return_value = charging_session
    mock_get_session.return_value = session

    repository.create_charging_session(charging_session)
    repository.update_charging_session(charging_session)

    assert repository.get_charging_session(1) == charging_session
    assert repository.get_charging_sessions_by_user(1) == [charging_session]
    assert repository.get_active_session_by_user(1) == charging_session

@patch("app.service.repository")
def test_get_charging_session_details_not_found(mock_repo):
    mock_repo.get_charging_session.return_value = None

    with pytest.raises(ValueError, match="Session tidak ditemukan"):
        service.get_charging_session_details(999)

@patch("app.service.repository")
def test_get_charging_session_details_invoice_none(mock_repo):
    session = MagicMock()
    session.id = 10
    session.user_id = 1
    session.asset_id = 2

    mock_repo.get_charging_session.return_value = session
    mock_repo.get_user.return_value = MagicMock()
    mock_repo.get_station_asset.return_value = MagicMock()
    mock_repo.get_invoice_by_session.return_value = None  # 🔥 INI KUNCINYA

    result = service.get_charging_session_details(10)

    assert result["invoice"] is None

@patch("app.service.repository")
def test_get_charging_session_details_success(mock_repo):
    session = MagicMock()
    session.id = 10
    session.user_id = 1
    session.asset_id = 2

    mock_repo.get_charging_session.return_value = session
    mock_repo.get_user.return_value = MagicMock()
    mock_repo.get_station_asset.return_value = MagicMock()
    mock_repo.get_invoice_by_session.return_value = MagicMock()

    result = service.get_charging_session_details(10)

    assert "user" in result
    assert "station_asset" in result
    assert "invoice" in result

# =====================================================
# STOP SESSION TRANSACTION
# =====================================================

@patch("app.repository.get_db_session")
def test_execute_stop_session_transaction(mock_get_session):
    session_db = mock_session()
    mock_get_session.return_value = session_db

    session = MagicMock()
    session.session_id = 1
    session.user_id = 1

    asset = MagicMock()
    details = {
        "end_time": MagicMock(),
        "duration_minutes": 60.123,
        "total_kwh": 10.5,
        "total_cost": 5000.456,
        "billing_total": 5500.789,
    }
    tariff = MagicMock()

    result = repository.execute_stop_session_transaction(
        session, asset, details, tariff
    )

    session_db.add.assert_called()
    session_db.commit.assert_called_once()
    session_db.refresh.assert_called_once_with(session)
    assert result == session


# =====================================================
# INVOICE
# =====================================================

@patch("app.repository.get_db_session")
def test_invoice_functions(mock_get_session):
    session = mock_session()
    invoice = MagicMock()
    session.get.return_value = invoice
    session.exec.return_value.all.return_value = [invoice]
    session.exec.return_value.first.return_value = invoice
    mock_get_session.return_value = session

    repository.create_invoice(invoice)
    repository.update_invoice(invoice)

    assert repository.get_invoice(1) == invoice
    assert repository.get_invoices_by_user(1) == [invoice]
    assert repository.get_invoice_by_session(1) == invoice
