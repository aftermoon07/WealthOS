"""Goals calculation engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from app.models.models import Goal


@dataclass
class GoalAnalysis:
    goal_id: int
    name: str
    goal_type: str
    target: Decimal
    current: Decimal
    progress_pct: Decimal
    remaining: Decimal
    target_date: Optional[date]
    monthly_contribution: Optional[Decimal]
    months_remaining: Optional[int]
    projected_value: Optional[Decimal]
    required_monthly: Optional[Decimal]
    on_track: Optional[bool]
    shortfall: Optional[Decimal]


def analyze_goal(goal: Goal, today: Optional[date] = None) -> GoalAnalysis:
    today = today or date.today()

    progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else Decimal("0")
    remaining = goal.target_amount - goal.current_amount

    months_remaining = None
    projected_value = None
    required_monthly = None
    on_track = None
    shortfall = None

    if goal.target_date:
        months_remaining = max(
            (goal.target_date.year - today.year) * 12 + goal.target_date.month - today.month,
            0,
        )

        if months_remaining > 0 and goal.monthly_contribution:
            # Simple projection: current + contributions (ignoring investment growth)
            projected_value = goal.current_amount + goal.monthly_contribution * months_remaining
            if goal.expected_return_pct and goal.expected_return_pct > 0:
                # Future value of annuity: FV = P * ((1+r)^n - 1) / r
                r = float(goal.expected_return_pct) / 100 / 12
                n = months_remaining
                fv_contributions = float(goal.monthly_contribution) * ((1 + r) ** n - 1) / r
                fv_current = float(goal.current_amount) * (1 + r) ** n
                projected_value = Decimal(str(round(fv_contributions + fv_current, 2)))

            on_track = projected_value >= goal.target_amount
            shortfall = max(goal.target_amount - projected_value, Decimal("0")) if projected_value else None

        # Required monthly to reach goal (no return assumption)
        if months_remaining > 0 and remaining > 0:
            required_monthly = (remaining / months_remaining).quantize(Decimal("0.01"))

    return GoalAnalysis(
        goal_id=goal.id,
        name=goal.name,
        goal_type=goal.goal_type.value,
        target=goal.target_amount,
        current=goal.current_amount,
        progress_pct=progress.quantize(Decimal("0.1")),
        remaining=remaining,
        target_date=goal.target_date,
        monthly_contribution=goal.monthly_contribution,
        months_remaining=months_remaining,
        projected_value=projected_value,
        required_monthly=required_monthly,
        on_track=on_track,
        shortfall=shortfall,
    )
