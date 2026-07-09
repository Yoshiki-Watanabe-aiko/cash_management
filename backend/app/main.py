from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.budgets import router as budgets_router
from app.api.category_rules import router as category_rules_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.reference import router as reference_router
from app.api.transactions import router as transactions_router
from app.api.transfers import router as transfers_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="統合資産・経費管理システム API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(reference_router)
app.include_router(dashboard_router)
app.include_router(transactions_router)
app.include_router(transfers_router)
app.include_router(budgets_router)
app.include_router(category_rules_router)
app.include_router(accounts_router)
