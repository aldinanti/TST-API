from datetime import datetime
from app import repository, models
from app.db import get_session as get_db_session

TARIFF_PER_KWH = 3000.0

def start_charging_session(user_id: int, charger_unit_id: int) -> models.ChargingSession:
    user = repository.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")

    charger = repository.get_charger(charger_unit_id)
    if not charger:
        raise ValueError("Charger unit tidak ditemukan")
    if not charger.is_available:
        raise ValueError("Charger sedang tidak tersedia")

    charger.is_available = False
    repository.update_charger(charger)

    session = models.ChargingSession(
        user_id=user_id,
        charger_unit_id=charger_unit_id,
        started_at=datetime.utcnow(),
        status="running"
    )
    session = repository.create_session(session)
    return session

def stop_charging_session(session_id: int) -> models.ChargingSession:
    session = repository.get_session(session_id)
    if not session:
        raise ValueError("Session tidak ditemukan")
    if session.status != "running":
        raise ValueError("Session bukan dalam status running")

    stopped_at = datetime.utcnow()
    started = session.started_at
    duration_seconds = (stopped_at - started).total_seconds()
    hours = duration_seconds / 3600.0

    charger = repository.get_charger(session.charger_unit_id)
    max_kw = charger.max_power_kw if charger else 7.0

    total_kwh = round(max_kw * hours, 3)
    cost = total_kwh * TARIFF_PER_KWH

    session.stopped_at = stopped_at
    session.total_kwh = total_kwh
    session.status = "stopped"
    repository.update_session(session)

    if charger:
        charger.is_available = True
        repository.update_charger(charger)

    with get_db_session() as s:
        payment = models.PaymentTransaction(
            charging_session_id=session.id,
            amount=cost,
            method="on_site",
            status="pending"
        )
        s.add(payment)
        s.commit()
        s.refresh(payment)

    return session