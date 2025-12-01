from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from datetime import timedelta
from app import db, repository, models, schemas, service
from app.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(
    title="EV Charging API",
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Setup templates dan static files
templates = Jinja2Templates(directory="app/html")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def on_startup():
    db.init_db()

# ===== CUSTOM SWAGGER UI WITH AUTH =====
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={
            "persistAuthorization": True,  # Remember auth
        }
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )

# ===== HALAMAN WEB =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage dengan link ke login/register"""
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Halaman login"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Halaman register"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Halaman dashboard (protected)"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ===== AUTH ENDPOINTS =====
@app.post("/auth/register", response_model=schemas.UserRead, tags=["Authentication"])
def register(user: schemas.UserRegister):
    """Registrasi user baru"""
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

@app.post("/auth/login", response_model=schemas.Token, tags=["Authentication"])
def login(credentials: schemas.UserLogin):
    """Login dan dapatkan JWT token"""
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

@app.get("/auth/me", response_model=schemas.UserRead, tags=["Authentication"])
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    user = repository.get_user(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user

# ===== PROTECTED ENDPOINTS =====

@app.post("/users", response_model=schemas.UserRead, tags=["Users"])
def create_user_u(u: schemas.UserCreate, current_user: dict = Depends(get_current_user)):
    """Create user (protected)"""
    user = models.User(name=u.name, email=u.email, phone=u.phone)
    created = repository.create_user(user)
    return created

@app.post("/stations", response_model=schemas.StationRead, tags=["Stations"])
def create_station(s: schemas.StationCreate, current_user: dict = Depends(get_current_user)):
    """Create station (protected)"""
    st = models.ChargingStation(name=s.name, location=s.location)
    return repository.create_station(st)

@app.get("/stations", response_model=list[schemas.StationRead], tags=["Stations"])
def list_stations():
    """List stations (public)"""
    sts = repository.list_stations()
    return sts

@app.post("/chargers", response_model=schemas.ChargerUnitRead, tags=["Chargers"])
def create_charger(c: schemas.ChargerUnitCreate, current_user: dict = Depends(get_current_user)):
    """Create charger (protected)"""
    ch = models.ChargerUnit(station_id=c.station_id, connector_type=c.connector_type, max_power_kw=c.max_power_kw)
    created = repository.create_charger(ch)
    return created

@app.post("/sessions", response_model=schemas.SessionRead, tags=["Charging Sessions"])
def start_session(req: schemas.StartSessionReq, current_user: dict = Depends(get_current_user)):
    """Start charging session (protected)"""
    try:
        if req.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda hanya bisa memulai session untuk diri sendiri"
            )
        
        session = service.start_charging_session(req.user_id, req.charger_unit_id)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/sessions/{session_id}/stop", response_model=schemas.SessionRead, tags=["Charging Sessions"])
def stop_session(session_id: int, current_user: dict = Depends(get_current_user)):
    """Stop charging session (protected)"""
    try:
        session = repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session tidak ditemukan")
        
        if session.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda hanya bisa menghentikan session milik sendiri"
            )
        
        session = service.stop_charging_session(session_id)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sessions/{session_id}", response_model=schemas.SessionRead, tags=["Charging Sessions"])
def get_session(session_id: int, current_user: dict = Depends(get_current_user)):
    """Get session detail (protected)"""
    s = repository.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    
    if s.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak berhak melihat session ini"
        )
    
    return s