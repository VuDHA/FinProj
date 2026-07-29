"""API routes for goal-based savings (Mục tiêu tiết kiệm)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Goal
from schemas import (
    GoalContribute,
    GoalCreate,
    GoalProgress,
    GoalRead,
    GoalSummary,
    GoalUpdate,
)
from services.goals import (
    contribute_to_goal,
    get_goal_progress,
    get_goals_summary,
    update_goal_timestamp,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=List[GoalRead])
def list_goals(session: Session = Depends(get_session)):
    """Liệt kê tất cả mục tiêu tiết kiệm."""
    return session.exec(select(Goal).order_by(Goal.created_at.desc())).all()


@router.post("/", response_model=GoalRead)
def create_goal(goal: GoalCreate, session: Session = Depends(get_session)):
    """Tạo mục tiêu tiết kiệm mới."""
    if goal.target_amount <= 0:
        raise HTTPException(status_code=400, detail="Target amount must be positive")
    db_goal = Goal(**goal.model_dump())
    session.add(db_goal)
    session.commit()
    session.refresh(db_goal)
    return db_goal


@router.get("/summary", response_model=GoalSummary)
def get_summary(session: Session = Depends(get_session)):
    """Tổng quan tất cả mục tiêu: tổng đã tiết kiệm vs tổng mục tiêu."""
    return get_goals_summary(session)


@router.get("/{goal_id}", response_model=GoalRead)
def get_goal(goal_id: int, session: Session = Depends(get_session)):
    """Lấy chi tiết một mục tiêu."""
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/{goal_id}", response_model=GoalRead)
def update_goal(goal_id: int, update: GoalUpdate, session: Session = Depends(get_session)):
    """Cập nhật mục tiêu tiết kiệm."""
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if update.name is not None:
        goal.name = update.name
    if update.target_amount is not None:
        if update.target_amount <= 0:
            raise HTTPException(status_code=400, detail="Target amount must be positive")
        goal.target_amount = update.target_amount
    if update.current_amount is not None:
        # NC11: Validate current_amount is non-negative and does not exceed target
        if update.current_amount < 0:
            raise HTTPException(status_code=400, detail="current_amount must be non-negative")
        if update.target_amount is not None:
            target = update.target_amount
        else:
            target = goal.target_amount
        if update.current_amount > target:
            raise HTTPException(status_code=400, detail="current_amount cannot exceed target_amount")
        goal.current_amount = update.current_amount
    if update.target_date is not None:
        goal.target_date = update.target_date
    if update.is_completed is not None:
        goal.is_completed = update.is_completed
    if update.color is not None:
        goal.color = update.color

    update_goal_timestamp(goal)
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def delete_goal(goal_id: int, session: Session = Depends(get_session)):
    """Xóa mục tiêu tiết kiệm."""
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    session.delete(goal)
    session.commit()
    return {"ok": True}


@router.post("/{goal_id}/contribute", response_model=GoalRead)
def contribute(goal_id: int, body: GoalContribute, session: Session = Depends(get_session)):
    """Đóng góp hoặc rút tiền khỏi mục tiêu.

    amount > 0: đóng góp thêm
    amount < 0: rút tiền
    """
    goal = session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if body.amount == 0:
        raise HTTPException(status_code=400, detail="Amount must be non-zero")

    return contribute_to_goal(session, goal, body.amount)
