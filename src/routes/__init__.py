from fastapi import APIRouter

from src.routes import assets, auth, envelopes, note, transactions

router = APIRouter()
router.include_router(assets.router)
router.include_router(envelopes.router)
router.include_router(transactions.router)
router.include_router(note.router)
router.include_router(auth.router)
