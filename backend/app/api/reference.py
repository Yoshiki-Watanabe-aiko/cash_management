from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Account, Category
from app.schemas.reference import AccountRead, CategoryRead

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return db.execute(select(Account).order_by(Account.id)).scalars().all()


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    return db.execute(select(Category).order_by(Category.id)).scalars().all()
