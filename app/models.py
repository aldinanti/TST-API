from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from enum import Enum

# ===== ENUMS =====
class ChargingStatus(str, Enum):
    NOT_STARTED = "Not Started"
    ONGOING = "Ongoing"
    STOPPED = "Stopped"

class PaymentStatus(str, Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"

# ===== VALUE OBJECTS =====
class Location(SQLModel):
    """Value Object untuk lokasi stasiun"""
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = "Unknown"

class ConnectorPort(SQLModel):
    """Value Object untuk port konektor"""
    standard_name: str = "Unknown"  # CCS, CHAdeMO, Type 2, etc
    max_power_supported: float = 0.0  # dalam kW

class MaintenanceLog(SQLModel):
    """Value Object untuk log maintenance"""
    error_log: Optional[str] = None
    date_time: datetime = Field(default_factory=datetime.utcnow)

class Tariff(SQLModel):
    """Value Object untuk tarif pengisian"""
    cost_per_kwh: float
    cost_per_minute: float

class ChargingReport(SQLModel):
    """Value Object untuk laporan charging"""
    id_session: int
    id_user: int
    location: Location
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]  # dalam menit
    total_kwh: Optional[float]

# ===== ACCOUNT CONTEXT =====
class User(SQLModel, table=True):
    """Entitas User dari Account Context"""
    __tablename__ = "user"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    phone: Optional[str] = None
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    vehicles: List["Vehicle"] = Relationship(back_populates="user")
    charging_sessions: List["ChargingSession"] = Relationship(back_populates="user")
    invoices: List["Invoice"] = Relationship(back_populates="user")

class Vehicle(SQLModel, table=True):
    """Entitas Vehicle dari Account Context"""
    __tablename__ = "vehicle"
    
    vehicle_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    nomor_plat: str = Field(unique=True)
    battery_capacity: float  # dalam kWh
    connector_port: ConnectorPort = Field(sa_column=Column(JSON))
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="vehicles")

# ===== STATION MANAGEMENT CONTEXT =====
class Station(SQLModel, table=True):
    """Entitas Station dari Station Management Context"""
    __tablename__ = "station"
    
    station_id: Optional[int] = Field(default=None, primary_key=True)
    station_operator: str
    location: Location = Field(sa_column=Column(JSON))
    connector_list: List[str] = Field(default=[], sa_column=Column(JSON))  # List connector types
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    station_assets: List["StationAsset"] = Relationship(back_populates="station")

class StationAsset(SQLModel, table=True):
    """Entitas StationAsset dari Station Management Context"""
    __tablename__ = "station_asset"

    asset_id: Optional[int] = Field(default=None, primary_key=True)
    station_id: int = Field(foreign_key="station.station_id")
    model: str
    connector_port: ConnectorPort = Field(sa_column=Column(JSON))
    maintenance_log: Optional[MaintenanceLog] = Field(default=None, sa_column=Column(JSON))
    is_available: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    station: Optional[Station] = Relationship(back_populates="station_assets")
    charging_sessions: List["ChargingSession"] = Relationship(back_populates="station_asset")

# ===== CHARGING SESSION CONTEXT =====
class ChargingSession(SQLModel, table=True):
    """Entitas ChargingSession - Aggregate Root dari Charging Session Context"""
    __tablename__ = "charging_session"
    
    session_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    asset_id: int = Field(foreign_key="station_asset.asset_id")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # dalam menit
    total_kwh: Optional[float] = None
    charging_status: ChargingStatus = Field(default=ChargingStatus.NOT_STARTED)
    battery_capacity: Optional[float] = None  # Snapshot dari vehicle
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="charging_sessions")
    station_asset: Optional[StationAsset] = Relationship(back_populates="charging_sessions")
    invoice: Optional["Invoice"] = Relationship(back_populates="charging_session")

# ===== BILLING CONTEXT =====
class Invoice(SQLModel, table=True):
    """Entitas Invoice dari Billing Context"""
    __tablename__ = "invoice"
    
    invoice_id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="charging_session.session_id", unique=True)
    user_id: int = Field(foreign_key="user.user_id")
    tariff: Tariff = Field(sa_column=Column(JSON))
    cost_total: float  # Total dari (kWh * tarif_kwh) + (menit * tarif_menit)
    billing_total: float  # Total setelah ditambah biaya layanan, pajak, dll
    payment_method: str
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    date_time: datetime = Field(default_factory=datetime.utcnow)
    charging_report: Optional[ChargingReport] = Field(default=None, sa_column=Column(JSON))
    
    # Relationships
    charging_session: Optional[ChargingSession] = Relationship(back_populates="invoice")
    user: Optional[User] = Relationship(back_populates="invoices")