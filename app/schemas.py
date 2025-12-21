from pydantic import BaseModel, EmailStr, ConfigDict, Field, ValidationError, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ===== SHARED / NESTED SCHEMAS =====
class LocationBase(BaseModel):
    latitude: float
    longitude: float
    address: str
    model_config = ConfigDict(from_attributes=True)

class ConnectorPortBase(BaseModel):
    standard_name: str
    max_power_supported: float
    model_config = ConfigDict(from_attributes=True)

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

    @field_validator("connector_port", mode="before")
    @classmethod
    def safe_connector_port(cls, v):
        # Fallback jika data connector_port di DB rusak/null
        if not v or not isinstance(v, (dict, object)):
            return ConnectorPortBase(standard_name="UNKNOWN", max_power_supported=0.0)
        if isinstance(v, dict):
            # Pastikan field required ada
            return v if "standard_name" in v else {**v, "standard_name": "UNKNOWN", "max_power_supported": 0.0}
        return v

# ===== STATION SCHEMAS =====
class StationCreate(BaseModel):
    station_operator: str
    location: LocationBase
    connector_list: List[str]

class StationRead(StationCreate):
    station_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("location", mode="before")
    @classmethod
    def safe_location(cls, v):
        # Fallback jika data location di DB rusak/null
        if not v:
            return LocationBase(latitude=0.0, longitude=0.0, address="Unknown")
        if isinstance(v, dict):
            return v if "latitude" in v else {**v, "latitude": 0.0, "longitude": 0.0, "address": "Unknown"}
        return v

class StationAssetCreate(BaseModel):
    station_id: int
    model: str
    connector_port: ConnectorPortBase
    maintenance_log: Optional[MaintenanceLogBase] = None

class StationAssetRead(StationAssetCreate):
    asset_id: Optional[int] = None
    is_available: Optional[bool] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_asset(cls, asset):
        return cls(
            asset_id=getattr(asset, "asset_id", None),
            station_id=getattr(asset, "station_id", None),
            model=getattr(asset, "model", "UNKNOWN"),

            connector_port=cls._safe_connector_port(asset),

            is_available=getattr(asset, "is_available", True),
            created_at=getattr(asset, "created_at", datetime.utcnow()),
            maintenance_log=getattr(asset, "maintenance_log", None),
        )

    @staticmethod
    def _safe_connector_port(asset) -> ConnectorPortBase:
        try:
            cp = getattr(asset, "connector_port", None)
            if cp:
                return ConnectorPortBase.model_validate(cp)
        except (ValidationError, ValueError, TypeError):
            pass
        return ConnectorPortBase(standard_name="UNKNOWN", max_power_supported=0.0)


class StationAssetUpdate(BaseModel):
    is_available: Optional[bool] = None
    maintenance_log: Optional[MaintenanceLogBase] = None

class StationDetail(StationRead):
    station_assets: List[StationAssetRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_station(cls, station, assets):
        # Defensive Coding: Handle jika location di DB null/rusak
        try:
            loc_data = getattr(station, "location", None)
            if loc_data:
                loc = LocationBase.model_validate(loc_data)
            else:
                raise ValueError("Location missing")
        except (ValidationError, ValueError, TypeError):
            loc = LocationBase(latitude=0.0, longitude=0.0, address="Location Data Missing")
        
        # Defensive Coding: Handle connector_list
        con_list = getattr(station, "connector_list", [])
        if con_list is None:
            con_list = []

        return cls(
            station_id=station.station_id,
            station_operator=station.station_operator,
            location=loc,
            connector_list=con_list,
            created_at=station.created_at,
            station_assets=[
                StationAssetRead.from_orm_asset(asset)
                for asset in assets
            ],
        )

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

    @field_validator("tariff", mode="before")
    @classmethod
    def safe_tariff(cls, v):
        # Fallback jika data tariff di DB rusak/null
        if not v:
            return TariffRead(cost_per_kwh=0.0, cost_per_minute=0.0)
        if isinstance(v, dict):
            return v if "cost_per_kwh" in v else {**v, "cost_per_kwh": 0.0, "cost_per_minute": 0.0}
        return v

class InvoiceUpdatePayment(BaseModel):
    payment_status: str
    payment_method: str

# ===== COMPOSITE DETAIL SCHEMAS =====
class ChargingSessionDetail(ChargingSessionRead):
    user: Optional[UserRead] = None
    station_asset: Optional[StationAssetRead] = None
    invoice: Optional[InvoiceRead] = None