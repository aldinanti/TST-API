import json
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///./ev_charging.db"

def custom_json_serializer(obj):
    """
    Custom serializer to handle:
    1. Datetime objects -> ISO Strings
    2. Pydantic/SQLModel objects -> JSON Dicts
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # Handle Pydantic v2 / SQLModel objects
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    
    # Handle older Pydantic versions (fallback)
    if hasattr(obj, "dict"):
        return obj.dict()
        
    raise TypeError(f"Type {type(obj)} not serializable")

def dumps(obj):
    return json.dumps(obj, default=custom_json_serializer)

# We inject our custom serializer into the engine
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args={"check_same_thread": False},
    json_serializer=dumps
)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)