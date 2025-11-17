from fastapi import FastAPI, HTTPException
from app import db, repository, models, schemas, service

app = FastAPI(title="EV Charging API")

@app.on_event("startup")
def on_startup():
    db.init_db()

# Users
@app.post("/users", response_model=schemas.UserRead)
def create_user_u(u: schemas.UserCreate):
    user = models.User(name=u.name, email=u.email, phone=u.phone)
    created = repository.create_user(user)
    return created

# Stations & Chargers
@app.post("/stations", response_model=schemas.StationRead)
def create_station(s: schemas.StationCreate):
    st = models.ChargingStation(name=s.name, location=s.location)
    return repository.create_station(st)

@app.get("/stations", response_model=list[schemas.StationRead])
def list_stations():
    sts = repository.list_stations()
    return sts

@app.post("/chargers", response_model=schemas.ChargerUnitRead)
def create_charger(c: schemas.ChargerUnitCreate):
    ch = models.ChargerUnit(station_id=c.station_id, connector_type=c.connector_type, max_power_kw=c.max_power_kw)
    created = repository.create_charger(ch)
    return created

# Charging sessions
@app.post("/sessions", response_model=schemas.SessionRead)
def start_session(req: schemas.StartSessionReq):
    try:
        session = service.start_charging_session(req.user_id, req.charger_unit_id)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/sessions/{session_id}/stop", response_model=schemas.SessionRead)
def stop_session(session_id: int):
    try:
        session = service.stop_charging_session(session_id)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sessions/{session_id}", response_model=schemas.SessionRead)
def get_session(session_id: int):
    s = repository.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s