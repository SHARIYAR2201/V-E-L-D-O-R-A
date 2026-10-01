from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import models as m
from ..db import get_db
from ..security import current_user
from ..services import achievements, context as ctx, planner

router = APIRouter(tags=["tracking"])


@router.get("/activities")
def activities(db: Session = Depends(get_db)):
    return [{"key": a.key, "category": a.category, "name": a.name, "met": a.met, "source": a.source} for a in db.query(m.MetActivity).order_by(m.MetActivity.category, m.MetActivity.met)]


class WorkoutIn(BaseModel):
    activity_key: str
    minutes: float = Field(gt=0, le=600)
    day: date | None = None
    intensity: int | None = Field(None, ge=1, le=10)
    sets: int | None = Field(None, ge=1, le=50)
    reps: int | None = Field(None, ge=1, le=500)


@router.post("/workouts", status_code=201)
def add_workout(b: WorkoutIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    if not u.profile.weight_kg:
        raise HTTPException(409, "Add your weight to your profile to estimate calories burned")
    try:
        kcal, met = planner.calories_for(db, b.activity_key, u.profile.weight_kg, b.minutes)
    except KeyError:
        raise HTTPException(404, "Unknown activity; see GET /api/activities")
    w = m.WorkoutLog(user_id=u.id, day=b.day or date.today(), activity_key=b.activity_key, minutes=b.minutes, intensity=b.intensity,
                     sets=b.sets, reps=b.reps, kcal_burned=kcal)
    db.add(w); db.commit()
    return {"id": w.id, "kcal_burned": kcal, "met": met, "formula": "MET x weight_kg x hours (estimate)", "new_achievements": achievements.evaluate(db, u)}


@router.get("/workouts")
def list_workouts(days: int = 30, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    return [{"id": r.id, "day": str(r.day), "activity_key": r.activity_key, "minutes": r.minutes, "kcal_burned": r.kcal_burned, "sets": r.sets, "reps": r.reps}
            for r in db.query(m.WorkoutLog).filter(m.WorkoutLog.user_id == u.id, m.WorkoutLog.day >= since).order_by(m.WorkoutLog.day.desc())]


def _hours(bed: str, wake: str) -> float:
    b = datetime.strptime(bed, "%H:%M"); w = datetime.strptime(wake, "%H:%M")
    if w <= b:
        w += timedelta(days=1)
    return round((w - b).seconds / 3600, 2)


class SleepIn(BaseModel):
    day: date | None = None
    bedtime: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    wake_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quality: int = Field(ge=1, le=10)


@router.post("/sleep", status_code=201)
def add_sleep(b: SleepIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    h = _hours(b.bedtime, b.wake_time)
    db.add(m.SleepLog(user_id=u.id, day=b.day or date.today(), bedtime=b.bedtime, wake_time=b.wake_time, hours=h, quality=b.quality)); db.commit()
    return {"hours": h}


@router.get("/sleep")
def list_sleep(days: int = 30, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services import insights
    rows = db.query(m.SleepLog).filter(m.SleepLog.user_id == u.id, m.SleepLog.day >= date.today() - timedelta(days=days)).order_by(m.SleepLog.day).all()
    logs = [{"day": str(r.day), "bedtime": r.bedtime, "wake_time": r.wake_time, "hours": r.hours, "quality": r.quality} for r in rows]
    return {"logs": logs, "insights": insights.sleep_insights(logs)}


class WaterIn(BaseModel):
    ml: float = Field(gt=0, le=3000)
    day: date | None = None


@router.post("/water", status_code=201)
def add_water(b: WaterIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    day = b.day or date.today()
    db.add(m.WaterLog(user_id=u.id, day=day, ml=b.ml)); db.commit()
    tg = ctx.targets(u.profile)
    total = ctx.water(db, u.id, day)
    return {"total_ml": total, "goal_ml": tg["water_ml"] if tg else None, "reminder": None if not tg or total >= tg["water_ml"] else f"{round(tg['water_ml'] - total)} ml to go"}


class WeightIn(BaseModel):
    weight_kg: float = Field(ge=25, le=400)
    waist_cm: float | None = Field(None, ge=30, le=250)
    day: date | None = None


@router.post("/weight", status_code=201)
def add_weight(b: WeightIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    day = b.day or date.today()
    row = db.query(m.WeightLog).filter_by(user_id=u.id, day=day).first()
    if row:
        row.weight_kg, row.waist_cm = b.weight_kg, b.waist_cm
    else:
        db.add(m.WeightLog(user_id=u.id, day=day, weight_kg=b.weight_kg, waist_cm=b.waist_cm))
    if day == date.today():
        u.profile.weight_kg = b.weight_kg
    db.commit()
    return {"new_achievements": achievements.evaluate(db, u)}


@router.get("/achievements")
def get_achievements(u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    earned = {a.key: a.earned_at for a in db.query(m.Achievement).filter_by(user_id=u.id)}
    return [{"key": k, "title": t, "earned": k in earned, "earned_at": str(earned[k]) if k in earned else None} for k, t in achievements.CATALOG.items()]
