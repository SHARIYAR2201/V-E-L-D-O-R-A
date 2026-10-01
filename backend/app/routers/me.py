from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import models as m
from ..db import get_db
from ..disclaimers import DISCLAIMERS
from ..security import current_user
from ..services import context as ctx, health, rules

router = APIRouter(tags=["profile"])


class ProfileIn(BaseModel):
    name: str | None = None
    age: int | None = Field(None, ge=10, le=110)
    sex: str | None = Field(None, pattern="^(male|female)$")
    height_cm: float | None = Field(None, ge=90, le=250)
    weight_kg: float | None = Field(None, ge=25, le=400)
    activity_level: str | None = Field(None, pattern="^(sedentary|light|moderate|active|very_active)$")
    goal_type: str | None = Field(None, pattern="^(lose|maintain|gain)$")
    target_weight_kg: float | None = Field(None, ge=25, le=400)
    target_date: date | None = None
    experience: str | None = Field(None, pattern="^(beginner|intermediate|advanced)$")
    diet_preferences: list[str] | None = None
    allergies: list[str] | None = None
    equipment: list[str] | None = None
    workout_preferences: dict | None = None
    conditions: list[str] | None = None


def _out(u: m.User) -> dict:
    p = u.profile
    d = {c: getattr(p, c) for c in ProfileIn.model_fields}
    d["target_date"] = str(p.target_date) if p.target_date else None
    return {"email": u.email, "role": u.role, "email_verified": u.email_verified, "profile": d, "disclaimers": DISCLAIMERS}


@router.get("/me")
def me(u: m.User = Depends(current_user)):
    return _out(u)


@router.put("/me/profile")
def update(body: ProfileIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    known = set(rules.CONDITIONS)
    for c in data.get("conditions") or []:
        if c not in known and not c.startswith("custom:"):
            raise HTTPException(422, f"Unknown condition '{c}'. Use one of {sorted(known)} or 'custom:<text>'.")
    for k, v in data.items():
        setattr(u.profile, k, v)
    if "weight_kg" in data and data["weight_kg"]:
        w = db.query(m.WeightLog).filter_by(user_id=u.id, day=date.today()).first()
        if not w:
            db.add(m.WeightLog(user_id=u.id, day=date.today(), weight_kg=data["weight_kg"]))
    db.commit()
    return _out(u)


@router.get("/conditions")
def conditions():
    return {"conditions": rules.CONDITIONS, "allergens": sorted(rules.ALLERGEN_KEYWORDS), "diets": sorted(rules.DIET_EXCLUDE), "disclaimers": DISCLAIMERS}


@router.get("/me/metrics")
def metrics(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    p = u.profile
    if not health.complete(p):
        raise HTTPException(409, "Profile incomplete: age, sex, height and weight are required")
    cur = health.metrics(p)
    hist = []
    for w in db.query(m.WeightLog).filter_by(user_id=u.id).order_by(m.WeightLog.day):
        b = health.bmi(w.weight_kg, p.height_cm)
        r = health.bmr(w.weight_kg, p.height_cm, p.age, p.sex)
        hist.append({"day": str(w.day), "weight_kg": w.weight_kg, "bmi": b, "bmr": r, "tdee": health.tdee(r, p.activity_level)})
    return {"current": cur, "history": hist, "targets": ctx.targets(p), "formula": "BMI = kg/m^2; BMR = Mifflin-St Jeor; TDEE = BMR x activity factor", "disclaimers": DISCLAIMERS}


@router.get("/me/dashboard")
def dashboard(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    p, today = u.profile, date.today()
    tg = ctx.targets(p)
    eaten = ctx.day_totals(db, u.id, today)
    return {"date": str(today), "targets": tg, "eaten": eaten, "burned_kcal": ctx.burned(db, u.id, today), "water_ml": ctx.water(db, u.id, today),
            "remaining_kcal": round(tg["kcal"] - eaten["kcal"]) if tg else None, "profile_complete": tg is not None, "disclaimers": DISCLAIMERS}
