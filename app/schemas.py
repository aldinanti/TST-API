from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ===== SHARED / NESTED SCHEMAS =====
class LocationBase(BaseModel):
    latitude: float
    longitude: float
    address: str

class ConnectorPortBase(BaseModel):
    standard_name: str
    max_power_supported: float

class MaintenanceLogBase(BaseModel):
    error_log: Optional[str] = None
    date_time: datetime

# ===== AUTH SCHEMAS =====
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ===== USER / VEHICLE SCHEMAS =====
class UserRead(BaseModel):
    user_id: int
    email: EmailStr
    phone: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class VehicleCreate(BaseModel):
    nomor_plat: str
    battery_capacity: float
    connector_port: ConnectorPortBase

class VehicleRead(VehicleCreate):
    vehicle_id: int
    user_id: int = Field(alias="user_id")
    
    model_config = ConfigDict(from_attributes=True)

# ===== STATION SCHEMAS =====
class StationCreate(BaseModel):
    station_operator: str
    location: LocationBase
    connector_list: List[str]

class StationRead(StationCreate):
    station_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class StationAssetCreate(BaseModel):
    station_id: int
    model: str
    connector_port: ConnectorPortBase
    maintenance_log: Optional[MaintenanceLogBase] = None

class StationAssetRead(StationAssetCreate):
    assets_id: int = Field(alias="asset_id")
    is_available: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, by_alias=True)

class StationAssetUpdate(BaseModel):
    is_available: Optional[bool] = None
    maintenance_log: Optional[MaintenanceLogBase] = None

class StationDetail(StationRead):
    station_assets: List[StationAssetRead] = []

# ===== CHARGING SESSION SCHEMAS =====
class ChargingSessionStart(BaseModel):
    asset_id: int

class ChargingSessionRead(BaseModel):
    session_id: int
    user_id: int
    asset_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    total_kwh: Optional[float] = None
    charging_status: str
    
    model_config = ConfigDict(from_attributes=True)

# ===== INVOICE SCHEMAS =====
class TariffRead(BaseModel):
    cost_per_kwh: float
    cost_per_minute: float

class InvoiceRead(BaseModel):
    invoice_id: int
    session_id: int
    cost_total: float
    billing_total: float
    payment_status: str
    payment_method: str
    date_time: datetime
    tariff: TariffRead
    
    model_config = ConfigDict(from_attributes=True)

class InvoiceUpdatePayment(BaseModel):
    payment_status: str
    payment_method: str

# ===== COMPOSITE DETAIL SCHEMAS =====
class ChargingSessionDetail(ChargingSessionRead):
    user: Optional[UserRead] = None
    station_asset: Optional[StationAssetRead] = None
    invoice: Optional[InvoiceRead] = None