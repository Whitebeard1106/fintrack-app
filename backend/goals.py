from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import SavingsGoal, User

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(BaseModel):
    name: str
    target_amount: float
    saved_amount: float = 0.0


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    saved_amount: Optional[float] = None


@router.get("/")
def list_goals(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return session.exec(select(SavingsGoal).where(SavingsGoal.user_id == current_user.id)).all()


@router.post("/")
def create_goal(
    body: GoalCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    goal = SavingsGoal(user_id=current_user.id, **body.model_dump())
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.put("/{goal_id}")
def update_goal(
    goal_id: int,
    body: GoalUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    goal = session.get(SavingsGoal, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    goal = session.get(SavingsGoal, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    session.delete(goal)
    session.commit()
    return {"ok": True}
