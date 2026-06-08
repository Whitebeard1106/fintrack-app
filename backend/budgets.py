from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import Budget, User

router = APIRouter(prefix="/budgets", tags=["budgets"])


class BudgetCreate(BaseModel):
    category: str
    limit_amount: float


class BudgetUpdate(BaseModel):
    limit_amount: float


@router.get("/")
def list_budgets(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return session.exec(select(Budget).where(Budget.user_id == current_user.id)).all()


@router.post("/")
def create_budget(
    body: BudgetCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    budget = Budget(user_id=current_user.id, **body.model_dump())
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


@router.put("/{budget_id}")
def update_budget(
    budget_id: int,
    body: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    budget = session.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Бюджет не найден")
    budget.limit_amount = body.limit_amount
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    budget = session.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Бюджет не найден")
    session.delete(budget)
    session.commit()
    return {"ok": True}
