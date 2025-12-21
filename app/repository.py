from sqlmodel import select
from app.db import get_session as get_db_session
from app import models
from typing import Optional, List
from sqlalchemy.orm import selectinload
from typing import Dict, Any

# ==========================================
# ACCOUNT CONTEXT (Users & Vehicles)
# ==========================================

def _save(instance: models.SQLModel) -> models.SQLModel:
    """Generic save (create or update) function."""
    with get_db_session() as s:
        s.add(instance)
        s.commit()
        s.refresh(instance)
    return instance

def create_user(user: models.User) -> models.User:
    return _save(user)

def get_user(user_id: int) -> Optional[models.User]:
    with get_db_session() as s:
        return s.get(models.User, user_id)

def get_user_by_email(email: str) -> Optional[models.User]:
    with get_db_session() as s:
        statement = select(models.User).where(models.User.email == email)
        result = s.exec(statement).first()
        return result

def list_users() -> List[models.User]:
    with get_db_session() as s:
        statement = select(models.User)
        return s.exec(statement).all()

def create_vehicle(vehicle: models.Vehicle) -> models.Vehicle:
    return _save(vehicle)

def get_vehicle(vehicle_id: int) -> Optional[models.Vehicle]:
    with get_db_session() as s:
        return s.get(models.Vehicle, vehicle_id)

def get_vehicle_by_plate(plate: str) -> Optional[models.Vehicle]:
    with get_db_session() as s:
        statement = select(models.Vehicle).where(models.Vehicle.nomor_plat == plate)
        return s.exec(statement).first()

def get_vehicles_by_user(user_id: int) -> List[models.Vehicle]:
    with get_db_session() as s:
        statement = select(models.Vehicle).where(models.Vehicle.user_id == user_id) 
        return s.exec(statement).all()


# ==========================================
# STATION MANAGEMENT CONTEXT
# ==========================================

def create_station(station: models.Station) -> models.Station:
    return _save(station)

def get_station(station_id: int):
    with get_db_session() as s:
        # Menggunakan .get() adalah cara paling efisien untuk mengambil objek berdasarkan primary key.
        station = s.get(models.Station, station_id)
        return station

def list_stations() -> List[models.Station]:
    with get_db_session() as s:
        statement = select(models.Station)
        return s.exec(statement).all()

def search_stations_by_operator(operator_name: str) -> List[models.Station]:
    with get_db_session() as s:
        # REFACTOR: Menggunakan .ilike() untuk pencarian case-insensitive dan parsial.
        statement = select(models.Station).where(models.Station.station_operator.ilike(f"%{operator_name}%"))
        return s.exec(statement).all()

# === Station Assets (Fixed: Changed from ChargerUnit to StationAsset) ===

def create_station_asset(asset: models.StationAsset) -> models.StationAsset:
    return _save(asset)

def get_station_asset(asset_id: int) -> Optional[models.StationAsset]:
    with get_db_session() as s:
        return s.get(models.StationAsset, asset_id)

def update_station_asset(asset: models.StationAsset) -> models.StationAsset:
    return _save(asset)

def get_station_assets_by_station(station_id: int) -> List[models.StationAsset]:
    with get_db_session() as s:
        statement = select(models.StationAsset).where(models.StationAsset.station_id == station_id)
        return s.exec(statement).all()

def get_available_station_assets(station_id: Optional[int] = None) -> List[models.StationAsset]:
    with get_db_session() as s:
        statement = select(models.StationAsset).where(models.StationAsset.is_available == True)
        if station_id:
            statement = statement.where(models.StationAsset.station_id == station_id)
        return s.exec(statement).all()


# ==========================================
# CHARGING SESSION CONTEXT
# ==========================================

def create_charging_session(session: models.ChargingSession) -> models.ChargingSession:
    return _save(session)

def get_charging_session(session_id: int) -> Optional[models.ChargingSession]:
    with get_db_session() as s:
        return s.get(models.ChargingSession, session_id)

def update_charging_session(session: models.ChargingSession) -> models.ChargingSession:
    return _save(session)

def get_charging_sessions_by_user(user_id: int) -> List[models.ChargingSession]:
    with get_db_session() as s:
        statement = select(models.ChargingSession).where(models.ChargingSession.user_id == user_id)  
        return s.exec(statement).all()

def get_active_session_by_user(user_id: int) -> Optional[models.ChargingSession]:
    with get_db_session() as s:
        # Check for sessions that are ONGOING
        statement = select(models.ChargingSession).where(
            models.ChargingSession.user_id == user_id,
            models.ChargingSession.charging_status == models.ChargingStatus.ONGOING
        )
        return s.exec(statement).first()

def execute_stop_session_transaction(
    session: models.ChargingSession,
    asset: models.StationAsset,
    details: Dict[str, Any],
    tariff: models.Tariff
) -> models.ChargingSession:
    """Executes all database operations for stopping a session in a single transaction."""
    with get_db_session() as s:
        # 1. Update Session
        session.end_time = details["end_time"]
        session.duration = round(details["duration_minutes"], 2)
        session.total_kwh = details["total_kwh"]
        session.charging_status = models.ChargingStatus.STOPPED
        s.add(session)

        # 2. Release Asset
        asset.is_available = True
        s.add(asset)

        # 3. Create Invoice
        invoice = models.Invoice(
            session_id=session.session_id,
            user_id=session.user_id,
            tariff=tariff,
            cost_total=round(details["total_cost"], 2),
            billing_total=round(details["billing_total"], 2),
            payment_method="N/A",
            payment_status=models.PaymentStatus.PENDING,
            date_time=details["end_time"]
        )
        s.add(invoice)

        s.commit()
        s.refresh(session)
        return session


# ==========================================
# BILLING CONTEXT (Invoices)
# ==========================================

def create_invoice(invoice: models.Invoice) -> models.Invoice:
    return _save(invoice)

def get_invoice(invoice_id: int) -> Optional[models.Invoice]:
    with get_db_session() as s:
        return s.get(models.Invoice, invoice_id)

def update_invoice(invoice: models.Invoice) -> models.Invoice:
    return _save(invoice)

def get_invoices_by_user(user_id: int) -> List[models.Invoice]:
    with get_db_session() as s:
        statement = select(models.Invoice).where(models.Invoice.user_id == user_id)
        return s.exec(statement).all()

def get_invoice_by_session(session_id: int) -> Optional[models.Invoice]:
    with get_db_session() as s:
        statement = select(models.Invoice).where(models.Invoice.session_id == session_id)
        return s.exec(statement).first()