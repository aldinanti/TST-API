from sqlmodel import select
from app.db import get_session as get_db_session
from app import models
from typing import Optional, List

def create_user(user: models.User) -> models.User:
    with get_db_session() as s:
        s.add(user)
        s.commit()
        s.refresh(user)
    return user

def get_user(user_id: int) -> Optional[models.User]:
    with get_db_session() as s:
        return s.get(models.User, user_id)

def get_user_by_email(email: str) -> Optional[models.User]:
    with get_db_session() as s:
        statement = select(models.User).where(models.User.email == email)
        result = s.exec(statement).first()
        return result

def create_station(station: models.ChargingStation) -> models.ChargingStation:
    with get_db_session() as s:
        s.add(station)
        s.commit()
        s.refresh(station)
    return station

def list_stations() -> List[models.ChargingStation]:
    with get_db_session() as s:
        statement = select(models.ChargingStation)
        return s.exec(statement).all()

def create_charger(unit: models.ChargerUnit) -> models.ChargerUnit:
    with get_db_session() as s:
        s.add(unit)
        s.commit()
        s.refresh(unit)
    return unit

def get_charger(charger_id: int) -> Optional[models.ChargerUnit]:
    with get_db_session() as s:
        return s.get(models.ChargerUnit, charger_id)

def update_charger(charger: models.ChargerUnit) -> models.ChargerUnit:
    with get_db_session() as s:
        s.add(charger)
        s.commit()
        s.refresh(charger)
    return charger

def create_session(session: models.ChargingSession) -> models.ChargingSession:
    with get_db_session() as s:
        s.add(session)
        s.commit()
        s.refresh(session)
    return session

def get_session(session_id: int) -> Optional[models.ChargingSession]:
    with get_db_session() as s:
        return s.get(models.ChargingSession, session_id)

def update_session(session: models.ChargingSession) -> models.ChargingSession:
    with get_db_session() as s:
        s.add(session)
        s.commit()
        s.refresh(session)
    return session