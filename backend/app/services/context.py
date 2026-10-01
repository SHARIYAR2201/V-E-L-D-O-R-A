from datetime import date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models as m
from . import health


def cond_set(p: m.Profile) -> set[str]:
    return set(p.conditions or [])


def day_totals(db: Session, uid: int, day: date) -> dict:
    r = db.query(func.coalesce(func.sum(m.FoodLog.kcal), 0), func.coalesce(func.sum(m.FoodLog.protein_g), 0), func.coalesce(func.sum(m.FoodLog.carb_g), 0),
                 func.coalesce(func.sum(m.FoodLog.fat_g), 0), func.coalesce(func.sum(m.FoodLog.fiber_g), 0)).filter_by(user_id=uid, day=day).one()
    return dict(zip(("kcal", "protein_g", "carb_g", "fat_g", "fiber_g"), (round(float(x), 1) for x in r)))


def burned(db: Session, uid: int, day: date) -> float:
    return round(float(db.query(func.coalesce(func.sum(m.WorkoutLog.kcal_burned), 0)).filter_by(user_id=uid, day=day).scalar()), 0)


def water(db: Session, uid: int, day: date) -> float:
    return float(db.query(func.coalesce(func.sum(m.WaterLog.ml), 0)).filter_by(user_id=uid, day=day).scalar())


def daily_food(db: Session, uid: int, days: int = 14) -> dict[date, dict]:
    since = date.today() - timedelta(days=days)
    out: dict[date, dict] = {}
    for r in db.query(m.FoodLog).filter(m.FoodLog.user_id == uid, m.FoodLog.day >= since):
        d = out.setdefault(r.day, {"kcal": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "fiber_g": 0})
        for k in d:
            d[k] += getattr(r, k)
    return out


def targets(p: m.Profile) -> dict | None:
    return health.targets(p, cond_set(p)) if health.complete(p) else None
