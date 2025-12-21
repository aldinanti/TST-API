from datetime import datetime
from typing import Optional, Union, Dict, Any
from app import repository, models
from app.schemas import StationDetail

# Default Tariff Configuration
DEFAULT_TARIFF = models.Tariff(
    cost_per_kwh=2500.0,
    cost_per_minute=100.0
)

def get_station_details(station_id: int) -> StationDetail:
    station = repository.get_station(station_id)
    if not station:
        raise ValueError("Station tidak ditemukan")

    assets = repository.get_station_assets_by_station(station_id)
    return StationDetail.from_orm_station(station, assets)

def start_charging_session(user_id: int, asset_id: int) -> models.ChargingSession:
    # 1. Validate User
    user = repository.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")
    
    # 2. Check for existing active session
    active_session = repository.get_active_session_by_user(user_id)
    if active_session:
        raise ValueError("Anda masih memiliki sesi charging yang aktif")

    # 3. Validate Station Asset
    asset = repository.get_station_asset(asset_id)
    if not asset:
        raise ValueError("Station Asset tidak ditemukan")
    if not asset.is_available:
        raise ValueError("Charger sedang tidak tersedia (Sedang digunakan atau Maintenance)")

    # 4. Lock Asset
    asset.is_available = False
    repository.update_station_asset(asset)

    # 5. Create Session
    session = models.ChargingSession(
        user_id=user_id,
        asset_id=asset_id,
        start_time=datetime.utcnow(),
        charging_status=models.ChargingStatus.ONGOING
    )
    return repository.create_charging_session(session)

def _calculate_session_details(session: models.ChargingSession, asset: models.StationAsset, manual_kwh: Optional[float] = None) -> Dict[str, Any]:
    # 1. Get Session
    if not session:
        raise ValueError("Session tidak ditemukan")
    if session.charging_status != models.ChargingStatus.ONGOING:
        raise ValueError("Session sudah berakhir")

    # 2. Calculate Metrics & Cost
    end_time = datetime.utcnow()
    duration_seconds = (end_time - session.start_time).total_seconds()
    duration_minutes = duration_seconds / 60.0
    duration_hours = duration_seconds / 3600.0

    # Refactored: Power is taken directly from the asset model
    max_kw = asset.connector_port.max_power_supported if asset and asset.connector_port else 7.0
    if manual_kwh is not None:
        total_kwh = manual_kwh
    else:
        # Simple simulation: Max Power * Duration
        total_kwh = round(max_kw * duration_hours, 3)

    # 4. Calculate Cost
    cost_details = _calculate_billing(total_kwh, duration_minutes)

    return {
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "total_kwh": total_kwh,
        **cost_details
    }

def _calculate_billing(kwh: float, minutes: float) -> Dict[str, Any]:
    """Calculates cost and total billing from consumption metrics."""
    cost_kwh = kwh * DEFAULT_TARIFF.cost_per_kwh
    cost_time = minutes * DEFAULT_TARIFF.cost_per_minute
    total_cost = cost_kwh + cost_time
    
    admin_fee = 2000.0 # Should be moved to a config file
    billing_total = total_cost + admin_fee
    
    return {
        "total_cost": total_cost,
        "billing_total": billing_total
    }

def stop_charging_session(session_id: int, manual_kwh: Optional[float] = None) -> models.ChargingSession:
    """Stops a charging session and generates an invoice in a single transaction."""
    session = repository.get_charging_session(session_id)
    if not session or session.charging_status != models.ChargingStatus.ONGOING:
        raise ValueError("Session tidak ditemukan atau sudah berakhir")

    asset = repository.get_station_asset(session.asset_id)
    if asset:
        # Calculate details before entering the transaction
        details = _calculate_session_details(session, asset, manual_kwh)

        # Use a transactional function from the repository
        return repository.execute_stop_session_transaction(
            session=session,
            asset=asset,
            details=details,
            tariff=DEFAULT_TARIFF
        )
    else:
        raise ValueError("Asset terkait sesi ini tidak ditemukan.")

def add_maintenance_log(asset_id: int, error_log: str) -> models.StationAsset:
    asset = repository.get_station_asset(asset_id)
    if not asset:
        raise ValueError("Asset tidak ditemukan")

    # Create log object
    log = models.MaintenanceLog(
        error_log=error_log,
        date_time=datetime.utcnow()
    )
    
    # Update asset
    asset.maintenance_log = log
    asset.is_available = False # Force unavailable
    
    return repository.update_station_asset(asset)

def update_invoice_payment(invoice_id: int, status: str, method: str) -> models.Invoice:
    invoice = repository.get_invoice(invoice_id)
    if not invoice:
        raise ValueError("Invoice tidak ditemukan")
    
    # Validate Enum
    try:
        new_status = models.PaymentStatus(status)
    except ValueError:
        raise ValueError(f"Status pembayaran tidak valid. Gunakan: {[e.value for e in models.PaymentStatus]}")

    invoice.payment_status = new_status
    invoice.payment_method = method
    
    return repository.update_invoice(invoice)

def get_charging_session_details(session_id: int):
    session = repository.get_charging_session(session_id)
    if not session:
        raise ValueError("Session tidak ditemukan")

    user = repository.get_user(session.user_id)
    asset = repository.get_station_asset(session.asset_id)
    invoice = repository.get_invoice_by_session(session_id)

    return {
        **session.__dict__,
        "user": user,
        "station_asset": asset,
        "invoice": invoice
    }