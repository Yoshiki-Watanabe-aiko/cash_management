from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Account, Category, Institution
from app.schemas.reference import AccountRead, CategoryRead, InstitutionRead
from app.services import account_management

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return account_management.list_accounts_detail(db)


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    return db.execute(select(Category).order_by(Category.id)).scalars().all()


@router.get("/institutions", response_model=list[InstitutionRead])
def list_institutions(db: Session = Depends(get_db)) -> list[Institution]:
    return db.execute(select(Institution).order_by(Institution.id)).scalars().all()
