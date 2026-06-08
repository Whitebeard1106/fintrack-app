from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import Transaction, User

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionCreate(BaseModel):
    date: str
    type: str
    category: str
    description: Optional[str] = None
    amount: float


class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None


@router.get("/")
def list_transactions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    statement = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
    )
    return session.exec(statement).all()


@router.post("/")
def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tx = Transaction(user_id=current_user.id, **body.model_dump())
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


@router.put("/{tx_id}")
def update_transaction(
    tx_id: int,
    body: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tx = session.get(Transaction, tx_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


@router.delete("/{tx_id}")
def delete_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tx = session.get(Transaction, tx_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")
    session.delete(tx)
    session.commit()
    return {"ok": True}
