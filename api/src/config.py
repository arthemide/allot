import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


# Database configuration
POSTGRESQL_CONNECTION_STRING = os.getenv("POSTGRESQL_CONNECTION_STRING")
if not POSTGRESQL_CONNECTION_STRING:
    raise ValueError("POSTGRESQL_CONNECTION_STRING environment variable is not set")

engine = create_engine(POSTGRESQL_CONNECTION_STRING)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for all models
Base = declarative_base()
