from fastapi import APIRouter

from src.routes.funds import router as funds_router
from src.routes.stocks import router as stock_router
from src.routes.transactions import router as transactions_router

router = APIRouter()

router.include_router(funds_router)
router.include_router(stock_router)
router.include_router(transactions_router)
