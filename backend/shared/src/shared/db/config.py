import os
import time
from functools import wraps
from typing import Callable, TypeVar

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_timeout=30,  # Wait up to 30s for a connection
    connect_args={
        "connect_timeout": 10,  # Connection timeout 10s
        "options": "-c statement_timeout=30000",  # Query timeout 30s
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Declarative base for all models
class Base(DeclarativeBase):
    pass


# Type variable for generic return type
T = TypeVar("T")


def check_db_health() -> tuple[bool, str]:
    """
    Check database connectivity.

    Returns:
        Tuple (is_healthy, message)
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True, "Database connection OK"
    except OperationalError as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"Connection failed: {e}"
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        return False, f"Unexpected error: {e}"


def with_db_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (OperationalError, DBAPIError),
) -> Callable:
    """
    Decorator for automatic retry on transient database errors.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each retry
        retryable_exceptions: Exception types to retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"DB operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"DB operation failed after {max_retries + 1} attempts: {e}"
                        )

            assert last_exception is not None
            raise last_exception

        return wrapper

    return decorator
