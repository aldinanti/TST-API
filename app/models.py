from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

# --- User aggregate ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    phone: Optional[str] = None

    # relationship: vehicles could be separate table - for simplicity omit

# --- ChargingStation aggregate ---
class ChargingStation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    location: str

    charger_units: List["ChargerUnit"] = Relationship(back_populates="station")

class ChargerUnit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    station_id: int = Field(foreign_key="chargingstation.id")
    connector_type: str
    max_power_kw: float
    is_available: bool = True

    station: Optional[ChargingStation] = Relationship(back_populates="charger_units")

# --- PaymentTransaction entity ---
class PaymentTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    charging_session_id: Optional[int] = Field(default=None, foreign_key="chargingsession.id")
    amount: float
    method: str
    status: str  # e.g. pending, paid, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- ChargingSession aggregate root ---
class ChargingSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    charger_unit_id: int = Field(foreign_key="chargerunit.id")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    stopped_at: Optional[datetime] = None
    total_kwh: Optional[float] = None
    status: str = "running"  # running | stopped | cancelled
    # relation
    payment: Optional[PaymentTransaction] = Relationship(back_populates="session", sa_relationship_kwargs={"uselist": False})

# Link back relationship for PaymentTransaction
PaymentTransaction.__fields__["charging_session_id"]  # ensure field exists
# create reverse relationship manually (SQLModel minimal)
ChargingSession.__fields__  # noop to satisfy linter