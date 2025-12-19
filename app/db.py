import json
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session

import os
from sqlmodel import SQLModel, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ev_charging.db"  # LOCAL fallback
)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

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

engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args=connect_args,
    json_serializer=dumps
)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)