from datetime import datetime
from typing import Optional, Union, Dict, Any
from app import repository, models

# Default Tariff Configuration
DEFAULT_TARIFF = models.Tariff(
    cost_per_kwh=2500.0,
    cost_per_minute=100.0
)

def start_charging_session(user_id: int, station_asset_id: int) -> models.ChargingSession:
    # 1. Validate User
    user = repository.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")
    
    # 2. Check for existing active session
    active_session = repository.get_active_session_by_user(user_id)
    if active_session:
        raise ValueError("Anda masih memiliki sesi charging yang aktif")

    # 3. Validate Station Asset
    asset = repository.get_station_asset(station_asset_id)
    if not asset:
        raise ValueError("Station Asset tidak ditemukan")
    if not asset.is_available:
        raise ValueError("Charger sedang tidak tersedia (Sedang digunakan atau Maintenance)")

    # 4. Lock Asset
    asset.is_available = False
    repository.update_station_asset(asset)

    # 5. Create Session
    session = models.ChargingSession(
        id_user=user_id,
        id_station_asset=station_asset_id,
        start_time=datetime.utcnow(),
        charging_status=models.ChargingStatus.ONGOING
    )
    return repository.create_charging_session(session)

def stop_charging_session(session_id: int, manual_kwh: Optional[float] = None) -> models.ChargingSession:
    # 1. Get Session
    session = repository.get_charging_session(session_id)
    if not session:
        raise ValueError("Session tidak ditemukan")
    if session.charging_status != models.ChargingStatus.ONGOING:
        raise ValueError("Session sudah berakhir")

    # 2. Calculate Metrics
    end_time = datetime.utcnow()
    duration_seconds = (end_time - session.start_time).total_seconds()
    duration_minutes = duration_seconds / 60.0
    duration_hours = duration_seconds / 3600.0

    # 3. Get asset to determine power output (Max kW)
    asset = repository.get_station_asset(session.id_station_asset)
    max_kw = 7.0 # Default fallback
    
    if asset and asset.connector_port:
        cp = asset.connector_port
        # SAFETY CHECK: Handle Dict (from DB) vs Object (from Code)
        if isinstance(cp, dict):
            max_kw = cp.get("max_power_supported", 7.0)
        elif hasattr(cp, "max_power_supported"):
            max_kw = cp.max_power_supported

    # Calculate kWh
    if manual_kwh is not None:
        total_kwh = manual_kwh
    else:
        # Simple simulation: Max Power * Duration
        total_kwh = round(max_kw * duration_hours, 3)

    # 4. Calculate Cost
    cost_kwh = total_kwh * DEFAULT_TARIFF.cost_per_kwh
    cost_time = duration_minutes * DEFAULT_TARIFF.cost_per_minute
    total_cost = cost_kwh + cost_time
    
    # Simple tax/admin fee calculation
    admin_fee = 2000.0
    billing_total = total_cost + admin_fee

    # 5. Update Session
    session.end_time = end_time
    session.duration = round(duration_minutes, 2)
    session.total_kwh = total_kwh
    session.charging_status = models.ChargingStatus.STOPPED
    updated_session = repository.update_charging_session(session)

    # 6. Release Asset
    if asset:
        asset.is_available = True
        repository.update_station_asset(asset)

    # 7. Create Invoice
    invoice = models.Invoice(
        id_session=session.id,
        id_user=session.id_user,
        tariff=DEFAULT_TARIFF,
        cost_total=round(total_cost, 2),
        billing_total=round(billing_total, 2),
        payment_method="N/A",  # Pending selection
        payment_status=models.PaymentStatus.PENDING,
        date_time=end_time
    )
    repository.create_invoice(invoice)

    return updated_session

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