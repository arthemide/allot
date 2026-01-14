"""
Decorators and utilities for error handling and retry logic.
"""

import time
import functools
from typing import Callable, Type, Tuple, Optional
from loguru import logger


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on error with exponential backoff.
    
    Args:
        max_retries: Maximum number of attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier factor for delay (exponential)
        exceptions: Tuple of exception types to catch
        
    Returns:
        Decorator
        
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
        def my_function():
            # Code that might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"Definitive failure after {max_retries + 1} attempts for {func.__name__}: {e}"
                        )
            
            # If we reach here, all attempts failed
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator
