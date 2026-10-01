from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..disclaimers import DISCLAIMERS
from ..security import current_user
from ..services import context as ctx, planner
from .. import models as m

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/diet")
def diet(days: int = Query(1, ge=1, le=7), u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    p = u.profile
    tg = ctx.targets(p)
    if tg is None:
        raise HTTPException(409, "Profile incomplete: age, sex, height and weight are required")
    if tg["blocked"]:
        return {"blocked": tg["blocked"], "targets": {k: tg[k] for k in ("kcal", "protein_g", "carb_g", "fat_g")}, "disclaimers": DISCLAIMERS}
    plan = planner.diet_plan(db, tg, ctx.cond_set(p), p.allergies or [], p.diet_preferences or [], days=days, start_idx=date.today().toordinal())
    plan["safety_notes"] = tg["notes"]
    plan["disclaimers"] = DISCLAIMERS
    return plan


class WorkoutReq(BaseModel):
    level: str | None = Field(None, pattern="^(beginner|intermediate|advanced)$")
    minutes: int = Field(45, ge=15, le=120)
    days_per_week: int | None = Field(None, ge=1, le=6)
    equipment: list[str] | None = None


@router.post("/workout")
def workout(b: WorkoutReq, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    p = u.profile
    if not p.weight_kg:
        raise HTTPException(409, "Add your weight to your profile first")
    plan = planner.workout_plan(db, p, ctx.cond_set(p), b.level or p.experience or "beginner", b.minutes, b.days_per_week,
                                b.equipment if b.equipment is not None else (p.equipment or []))
    plan["disclaimers"] = DISCLAIMERS
    return plan
