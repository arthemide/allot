import asyncio
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from shared.logger import setup_logging
from src.routes import router
from src.services.alerts import run_alert_check

setup_logging()


def _read_interval_hours() -> float:
    raw = os.getenv("ALERT_CHECK_INTERVAL_HOURS", "24")
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            f"Invalid ALERT_CHECK_INTERVAL_HOURS={raw!r}; falling back to 24h"
        )
        return 24.0
    if value <= 0:
        logger.warning(
            f"Non-positive ALERT_CHECK_INTERVAL_HOURS={value}; falling back to 24h"
        )
        return 24.0
    return value


async def _alert_check_job() -> None:
    """Awaitable wrapper so APScheduler captures exceptions properly."""
    await asyncio.to_thread(run_alert_check)


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval_hours = _read_interval_hours()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _alert_check_job,
        trigger=IntervalTrigger(hours=interval_hours),
        id="alert_check",
        name="Stock alert threshold check",
        replace_existing=True,
    )
    scheduler.start()
    next_run = scheduler.get_job("alert_check").next_run_time
    logger.info(
        f"Alert scheduler started; interval={interval_hours}h, next run at {next_run}"
    )
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Alert scheduler stopped")


app = FastAPI(
    title="Stock Alerting API",
    description="API for stock search and portfolio management",
    lifespan=lifespan,
)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return "Stock stock stock! It's working!"
