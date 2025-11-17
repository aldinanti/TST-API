from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

class UserRead(UserCreate):
    id: int

class StationCreate(BaseModel):
    name: str
    location: str

class StationRead(StationCreate):
    id: int

class ChargerUnitCreate(BaseModel):
    station_id: int
    connector_type: str
    max_power_kw: float

class ChargerUnitRead(ChargerUnitCreate):
    id: int
    is_available: bool

class StartSessionReq(BaseModel):
    user_id: int
    charger_unit_id: int

class SessionRead(BaseModel):
    id: int
    user_id: int
    charger_unit_id: int
    started_at: datetime
    stopped_at: Optional[datetime] = None
    total_kwh: Optional[float] = None
    status: str