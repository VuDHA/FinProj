"""Business logic for goal-based savings (Mục tiêu tiết kiệm)."""

import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import text
from sqlmodel import Session, select

from models import Goal
from schemas import GoalProgress, GoalSummary


def calculate_progress(goal: Goal) -> float:
    """Tính phần trăm tiến độ của mục tiêu (current / target * 100)."""
    if goal.target_amount <= 0:
        return 0.0
    return float((goal.current_amount / goal.target_amount * Decimal("100")).quantize(Decimal("0.01")))


def get_goal_progress(goal: Goal) -> GoalProgress:
    """Trả về thông tin tiến độ chi tiết của một mục tiêu."""
    progress_percent = calculate_progress(goal)
    remaining = (goal.target_amount - goal.current_amount).quantize(Decimal("0.01"))
    return GoalProgress(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        progress_percent=progress_percent,
        remaining=remaining,
        is_completed=goal.is_completed,
        target_date=goal.target_date,
    )


def check_completion(goal: Goal) -> bool:
    """Kiểm tra xem mục tiêu đã hoàn thành chưa (current >= target)."""
    return goal.current_amount >= goal.target_amount and goal.target_amount > 0


def contribute_to_goal(session: Session, goal: Goal, amount: Decimal) -> Goal:
    """Cộng/trừ tiền vào current_amount và cập nhật trạng thái hoàn thành.

    amount > 0: đóng góp thêm
    amount < 0: rút tiền

    Uses atomic SQL UPDATE to prevent race condition (NC4).
    """
    # Atomic increment to prevent race condition
    session.execute(
        text("UPDATE goal SET current_amount = current_amount + :amount WHERE id = :id"),
        {"amount": float(amount), "id": goal.id},
    )
    session.commit()
    session.refresh(goal)

    # Clamp to non-negative
    if goal.current_amount < 0:
        session.execute(
            text("UPDATE goal SET current_amount = 0 WHERE id = :id"),
            {"id": goal.id},
        )
        session.commit()
        session.refresh(goal)

    # Update completion status
    if check_completion(goal):
        goal.is_completed = True
    elif goal.current_amount < goal.target_amount:
        goal.is_completed = False
    goal.updated_at = datetime.datetime.now().isoformat()
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


def get_goals_summary(session: Session) -> GoalSummary:
    """Tính tổng quan tất cả mục tiêu: tổng đã tiết kiệm, tổng mục tiêu, số lượng."""
    goals: List[Goal] = session.exec(select(Goal)).all()
    total_saved = sum((g.current_amount for g in goals), Decimal("0")).quantize(Decimal("0.01"))
    total_target = sum((g.target_amount for g in goals), Decimal("0")).quantize(Decimal("0.01"))
    active_count = sum(1 for g in goals if not g.is_completed)
    completed_count = sum(1 for g in goals if g.is_completed)

    if total_target > 0:
        overall_percent = float(
            (total_saved / total_target * Decimal("100")).quantize(Decimal("0.01"))
        )
    else:
        overall_percent = 0.0

    return GoalSummary(
        total_saved=total_saved,
        total_target=total_target,
        overall_progress_percent=overall_percent,
        active_goals=active_count,
        completed_goals=completed_count,
    )


def update_goal_timestamp(goal: Goal) -> Goal:
    """Cập nhật updated_at khi sửa đổi mục tiêu."""
    goal.updated_at = datetime.datetime.now().isoformat()
    return goal
