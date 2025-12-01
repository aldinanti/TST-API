from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from datetime import timedelta
from typing import List, Optional
from app import db, repository, models, schemas, service
from app.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(
    title="EV Charging Management API",
    description="Platform Manajemen Pengisian Baterai Kendaraan Listrik",
    version="2.0.0",
    docs_url=None,
    redoc_url=None
)

# Setup templates dan static files (jika ada)
try:
    templates = Jinja2Templates(directory="app/html")
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except:
    templates = None

@app.on_event("startup")
def on_startup():
    db.init_db()
    print("Database initialized successfully!")

# ===== CUSTOM SWAGGER UI =====
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={"persistAuthorization": True}
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(title=app.title, version="2.0.0", routes=app.routes)

# ===== ROOT ENDPOINT =====
@app.get("/", tags=["Root"])
def root():
    """API Root - Health Check"""
    return {
        "message": "EV Charging Management API",
        "version": "2.0.0",
        "docs": "/docs",
        "bounded_contexts": [
            "Account Context",
            "Station Management Context",
            "Charging Session Context",
            "Billing Context"
        ]
    }

# ===== AUTHENTICATION ENDPOINTS (Account Context) =====
@app.post("/auth/register", response_model=schemas.UserRead, tags=["1. Authentication"])
def register(user: schemas.UserRegister):
    """
    Registrasi user baru
    
    Business Rules:
    - Email harus unique
    - Password akan di-hash sebelum disimpan
    """
    existing_user = repository.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar"
        )
    
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password_hash=hashed_password
    )
    created = repository.create_user(new_user)
    return created

@app.post("/auth/login", response_model=schemas.Token, tags=["1. Authentication"])
def login(credentials: schemas.UserLogin):
    """
    Login dan dapatkan JWT access token
    
    Token ini digunakan untuk mengakses endpoint yang memerlukan autentikasi.
    Gunakan format: Authorization: Bearer <token>
    """
    user = repository.get_user_by_email(credentials.email)
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=schemas.UserRead, tags=["1. Authentication"])
def get_me(current_user: dict = Depends(get_current_user)):
    """Get informasi user yang sedang login"""
    user = repository.get_user(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user

# ===== USER ENDPOINTS (Account Context) =====
@app.get("/users", response_model=List[schemas.UserRead], tags=["2. Users (Account Context)"])
def list_users(current_user: dict = Depends(get_current_user)):
    """List semua users (admin only in production)"""
    return repository.list_users()

@app.get("/users/{user_id}", response_model=schemas.UserRead, tags=["2. Users (Account Context)"])
def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get detail user berdasarkan ID"""
    user = repository.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user

# ===== VEHICLE ENDPOINTS (Account Context) =====
@app.post("/vehicles", response_model=schemas.VehicleRead, tags=["2. Users (Account Context)"])
def create_vehicle(vehicle: schemas.VehicleCreate, current_user: dict = Depends(get_current_user)):
    """
    Daftarkan kendaraan baru untuk user yang sedang login
    
    Vehicle diperlukan untuk tracking battery capacity saat charging
    """
    # Check duplicate plate number
    existing = repository.get_vehicle_by_plate(vehicle.nomor_plat)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nomor plat sudah terdaftar"
        )
    
    new_vehicle = models.Vehicle(
        id_user=current_user["user_id"],
        nomor_plat=vehicle.nomor_plat,
        battery_capacity=vehicle.battery_capacity,
        connector_port=models.ConnectorPort(**vehicle.connector_port.dict())
    )
    created = repository.create_vehicle(new_vehicle)
    return created

@app.get("/vehicles/me", response_model=List[schemas.VehicleRead], tags=["2. Users (Account Context)"])
def get_my_vehicles(current_user: dict = Depends(get_current_user)):
    """Get semua kendaraan milik user yang sedang login"""
    return repository.get_vehicles_by_user(current_user["user_id"])

@app.get("/vehicles/{vehicle_id}", response_model=schemas.VehicleRead, tags=["2. Users (Account Context)"])
def get_vehicle(vehicle_id: int, current_user: dict = Depends(get_current_user)):
    """Get detail kendaraan berdasarkan ID"""
    vehicle = repository.get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle tidak ditemukan")
    
    # Check ownership
    if vehicle.id_user != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke kendaraan ini"
        )
    
    return vehicle

# ===== STATION ENDPOINTS (Station Management Context) =====
@app.post("/stations", response_model=schemas.StationRead, tags=["3. Stations (Station Management)"])
def create_station(station: schemas.StationCreate, current_user: dict = Depends(get_current_user)):
    """
    Buat stasiun charging baru (admin only in production)
    
    Station merepresentasikan lokasi fisik tempat charging
    """
    new_station = models.Station(
        station_operator=station.station_operator,
        location=models.Location(**station.location.dict()),
        connector_list=station.connector_list
    )
    created = repository.create_station(new_station)
    return created

@app.get("/stations", response_model=List[schemas.StationRead], tags=["3. Stations (Station Management)"])
def list_stations():
    """List semua stasiun charging (public endpoint)"""
    return repository.list_stations()

@app.get("/stations/{station_id}", response_model=schemas.StationDetail, tags=["3. Stations (Station Management)"])
def get_station(station_id: int):
    """Get detail stasiun beserta asset-assetnya"""
    station = repository.get_station(station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station tidak ditemukan")
    
    # Get station assets
    assets = repository.get_station_assets_by_station(station_id)
    
    return schemas.StationDetail(
        id=station.id,
        station_operator=station.station_operator,
        location=station.location,
        connector_list=station.connector_list,
        created_at=station.created_at,
        station_assets=[schemas.StationAssetRead.from_orm(a) for a in assets]
    )

# ===== STATION ASSET ENDPOINTS (Station Management Context) =====
@app.post("/station-assets", response_model=schemas.StationAssetRead, tags=["3. Stations (Station Management)"])
def create_station_asset(asset: schemas.StationAssetCreate, current_user: dict = Depends(get_current_user)):
    """
    Tambah asset (charger unit) ke stasiun
    
    Station Asset merepresentasikan mesin fisik charger
    """
    # Validate station exists
    station = repository.get_station(asset.station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station tidak ditemukan")
    
    new_asset = models.StationAsset(
        station_id=asset.station_id,
        model=asset.model,
        connector_port=models.ConnectorPort(**asset.connector_port.dict()),
        maintenance_log=models.MaintenanceLog(**asset.maintenance_log.dict()) if asset.maintenance_log else None
    )
    created = repository.create_station_asset(new_asset)
    return created

@app.get("/station-assets", response_model=List[schemas.StationAssetRead], tags=["3. Stations (Station Management)"])
def list_station_assets(
    station_id: Optional[int] = Query(None, description="Filter by station ID"),
    available_only: bool = Query(False, description="Show only available assets")
):
    """List station assets dengan filter optional"""
    if available_only:
        return repository.get_available_station_assets(station_id)
    elif station_id:
        return repository.get_station_assets_by_station(station_id)
    else:
        # Return all (implement if needed)
        raise HTTPException(status_code=400, detail="Provide station_id or set available_only=true")

@app.get("/station-assets/{asset_id}", response_model=schemas.StationAssetRead, tags=["3. Stations (Station Management)"])
def get_station_asset(asset_id: int):
    """Get detail station asset"""
    asset = repository.get_station_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Station asset tidak ditemukan")
    return asset

@app.patch("/station-assets/{asset_id}", response_model=schemas.StationAssetRead, tags=["3. Stations (Station Management)"])
def update_station_asset(
    asset_id: int,
    update: schemas.StationAssetUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update station asset (availability, maintenance log)"""
    asset = repository.get_station_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Station asset tidak ditemukan")
    
    if update.is_available is not None:
        asset.is_available = update.is_available
    if update.maintenance_log is not None:
        asset.maintenance_log = models.MaintenanceLog(**update.maintenance_log.dict())
    
    updated = repository.update_station_asset(asset)
    return updated

@app.post("/station-assets/{asset_id}/maintenance", response_model=schemas.StationAssetRead, tags=["3. Stations (Station Management)"])
def add_maintenance_log(
    asset_id: int,
    error_log: str,
    current_user: dict = Depends(get_current_user)
):
    """Tambahkan maintenance log dan set asset menjadi unavailable"""
    try:
        updated = service.add_maintenance_log(asset_id, error_log)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== CHARGING SESSION ENDPOINTS (Charging Session Context) =====
@app.post("/charging-sessions/start", response_model=schemas.ChargingSessionRead, tags=["4. Charging Sessions"])
def start_charging_session(
    req: schemas.ChargingSessionStart,
    current_user: dict = Depends(get_current_user)
):
    """
    Mulai sesi charging baru
    
    Business Rules:
    - User tidak boleh memiliki sesi aktif lain
    - Station asset harus tersedia
    - Station asset akan di-set unavailable saat charging
    """
    try:
        session = service.start_charging_session(
            user_id=current_user["user_id"],
            station_asset_id=req.id_station_asset
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/charging-sessions/{session_id}/stop", response_model=schemas.ChargingSessionRead, tags=["4. Charging Sessions"])
def stop_charging_session(
    session_id: int,
    kwh_consumed: Optional[float] = Query(None, description="Actual kWh consumed (optional)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Hentikan sesi charging
    
    - Menghitung durasi, kWh, dan biaya
    - Membuat invoice otomatis
    - Station asset dikembalikan ke status available
    """
    # Validate ownership
    session = repository.get_charging_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if session.id_user != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak berhak menghentikan session ini"
        )
    
    try:
        stopped_session = service.stop_charging_session(session_id, kwh_consumed)
        return stopped_session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/charging-sessions/me", response_model=List[schemas.ChargingSessionRead], tags=["4. Charging Sessions"])
def get_my_sessions(current_user: dict = Depends(get_current_user)):
    """Get semua charging sessions milik user yang sedang login"""
    return repository.get_charging_sessions_by_user(current_user["user_id"])

@app.get("/charging-sessions/me/active", response_model=schemas.ChargingSessionDetail, tags=["4. Charging Sessions"])
def get_my_active_session(current_user: dict = Depends(get_current_user)):
    """Get sesi charging aktif user (jika ada)"""
    session = repository.get_active_session_by_user(current_user["user_id"])
    if not session:
        raise HTTPException(status_code=404, detail="Tidak ada sesi aktif")
    
    return schemas.ChargingSessionDetail(
        id=session.id,
        id_user=session.id_user,
        id_station_asset=session.id_station_asset,
        start_time=session.start_time,
        end_time=session.end_time,
        duration=session.duration,
        total_kwh=session.total_kwh,
        charging_status=session.charging_status,
        battery_capacity=session.battery_capacity
    )

@app.get("/charging-sessions/{session_id}", response_model=schemas.ChargingSessionDetail, tags=["4. Charging Sessions"])
def get_charging_session(session_id: int, current_user: dict = Depends(get_current_user)):
    """Get detail charging session beserta relasi-nya"""
    session = repository.get_charging_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    
    # Check ownership
    if session.id_user != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak berhak melihat session ini"
        )
    
    # Get related data
    user = repository.get_user(session.id_user)
    asset = repository.get_station_asset(session.id_station_asset)
    invoice = repository.get_invoice_by_session(session_id)
    
    return schemas.ChargingSessionDetail(
        id=session.id,
        id_user=session.id_user,
        id_station_asset=session.id_station_asset,
        start_time=session.start_time,
        end_time=session.end_time,
        duration=session.duration,
        total_kwh=session.total_kwh,
        charging_status=session.charging_status,
        battery_capacity=session.battery_capacity,
        user=schemas.UserRead.from_orm(user) if user else None,
        station_asset=schemas.StationAssetRead.from_orm(asset) if asset else None,
        invoice=schemas.InvoiceRead.from_orm(invoice) if invoice else None
    )

# ===== INVOICE ENDPOINTS (Billing Context) =====
@app.get("/invoices/me", response_model=List[schemas.InvoiceRead], tags=["5. Invoices (Billing Context)"])
def get_my_invoices(current_user: dict = Depends(get_current_user)):
    """Get semua invoice milik user yang sedang login"""
    return repository.get_invoices_by_user(current_user["user_id"])

@app.get("/invoices/{invoice_id}", response_model=schemas.InvoiceRead, tags=["5. Invoices (Billing Context)"])
def get_invoice(invoice_id: int, current_user: dict = Depends(get_current_user)):
    """Get detail invoice"""
    invoice = repository.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    
    # Check ownership
    if invoice.id_user != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak berhak melihat invoice ini"
        )
    
    return invoice

@app.patch("/invoices/{invoice_id}/payment", response_model=schemas.InvoiceRead, tags=["5. Invoices (Billing Context)"])
def update_invoice_payment(
    invoice_id: int,
    payment_update: schemas.InvoiceUpdatePayment,
    current_user: dict = Depends(get_current_user)
):
    """
    Update status pembayaran invoice
    
    Untuk simulasi pembayaran (dalam production akan terintegrasi dengan payment gateway)
    """
    invoice = repository.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    
    # Check ownership
    if invoice.id_user != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak berhak mengupdate invoice ini"
        )
    
    try:
        updated = service.update_invoice_payment(
            invoice_id,
            payment_update.payment_status,
            payment_update.payment_method
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))