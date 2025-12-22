from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.logger import setup_logging
from src.routes import router

setup_logging()

app = FastAPI(
    title="Stock Alerting API",
    description="API for stock search and portfolio management",
)

app.include_router(router)


# Configure CORS to allow requests from the frontend
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
