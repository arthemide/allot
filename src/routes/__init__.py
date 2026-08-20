from fastapi import APIRouter

from src.routes import assets, transactions

router = APIRouter()
router.include_router(assets.router)
router.include_router(transactions.router)
