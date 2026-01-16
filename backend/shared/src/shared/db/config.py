import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


# Database configuration
POSTGRESQL_CONNECTION_STRING = os.getenv("POSTGRESQL_CONNECTION_STRING")
if not POSTGRESQL_CONNECTION_STRING:
    raise ValueError("POSTGRESQL_CONNECTION_STRING environment variable is not set")

# Create engine with connection pooling
engine = create_engine(
    POSTGRESQL_CONNECTION_STRING,
    pool_size=5,  # Connections in pool
    max_overflow=10,  # Extra connections allowed
    pool_pre_ping=True,  # Verify connections before use
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for all models
Base = declarative_base()
