from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import models as m
from ..db import get_db
from ..disclaimers import DISCLAIMERS
from ..security import current_user
from ..services import assistant, context as ctx, insights

router = APIRouter(prefix="/ai", tags=["ai"])


class Ask(BaseModel):
    message: str = Field(min_length=1, max_length=500)


@router.post("/assistant")
def ask(b: Ask, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return assistant.answer(db, u, b.message)


@router.get("/insights")
def get_insights(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    p, today = u.profile, date.today()
    tg = ctx.targets(p)
    wl = [(r.day, r.weight_kg) for r in db.query(m.WeightLog).filter_by(user_id=u.id)]
    food = ctx.daily_food(db, u.id, 28)
    wdays = {r[0] for r in db.query(m.WorkoutLog.day).filter(m.WorkoutLog.user_id == u.id, m.WorkoutLog.day >= today - timedelta(days=28))}
    return {
        "weight_trend": insights.weight_forecast(wl, target=p.target_weight_kg),
        "consistency": insights.consistency(set(food), wdays, today),
        "nutrition_adherence": insights.nutrition_adherence(food, tg) if tg else {"available": False, "reason": "Complete your profile."},
        "behaviour_patterns": insights.behaviour_patterns({d: v["kcal"] for d, v in food.items()}),
        "rule_priority": "Rules (conditions, allergies, diet, safety) always override any model output.",
        "disclaimers": DISCLAIMERS,
    }
