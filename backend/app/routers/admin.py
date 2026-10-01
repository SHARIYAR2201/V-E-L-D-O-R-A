import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import cache, models as m
from ..config import settings
from ..db import get_db
from ..security import admin_only
from ..services import nutrition

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_only)])


def _art(name):
    p = Path(settings.artifacts_dir) / name
    return json.loads(p.read_text()) if p.exists() else None


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    c = lambda t: db.query(func.count()).select_from(t).scalar()
    return {"users": c(m.User), "food_logs": c(m.FoodLog), "workout_logs": c(m.WorkoutLog), "sleep_logs": c(m.SleepLog), "foods_in_db": c(m.Food),
            "met_activities": c(m.MetActivity)}


@router.get("/users")
def users(db: Session = Depends(get_db)):
    return [{"id": u.id, "email": u.email, "role": u.role, "active": u.is_active, "verified": u.email_verified, "created": str(u.created_at)} for u in db.query(m.User).order_by(m.User.id)]


class UserPatch(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(None, pattern="^(user|admin)$")


@router.patch("/users/{uid}")
def patch_user(uid: int, b: UserPatch, db: Session = Depends(get_db)):
    u = db.get(m.User, uid)
    if not u:
        raise HTTPException(404, "Not found")
    for k, v in b.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    db.commit()
    return {"id": u.id, "role": u.role, "active": u.is_active}


class FoodIn(BaseModel):
    description: str = Field(min_length=3, max_length=300)
    kcal: float = Field(ge=0, le=950)
    protein_g: float = Field(0, ge=0, le=100)
    carb_g: float = Field(0, ge=0, le=100)
    fat_g: float = Field(0, ge=0, le=100)
    fiber_g: float | None = Field(None, ge=0, le=100)
    source: str = Field(min_length=3, description="Where the values come from (required; must be an approved dataset or label)")


@router.post("/foods", status_code=201)
def add_food(b: FoodIn, db: Session = Depends(get_db)):
    fid = (db.query(func.max(m.Food.fdc_id)).scalar() or 0) + 1
    db.add(m.Food(fdc_id=max(fid, 9_000_000), **b.model_dump()))
    db.commit(); nutrition.reset_cache()
    return {"fdc_id": max(fid, 9_000_000)}


@router.delete("/foods/{fdc_id}", status_code=204)
def del_food(fdc_id: int, db: Session = Depends(get_db)):
    f = db.get(m.Food, fdc_id)
    if not f or fdc_id < 9_000_000:
        raise HTTPException(404, "Only admin-added foods can be deleted")
    db.delete(f); db.commit(); nutrition.reset_cache()


@router.get("/datasets")
def datasets():
    return {"ingest": _art("ingest_report.json"), "models": _art("model_metrics.json"), "survey": _art("survey_summary.json"), "sleep_benchmarks": _art("sleep_benchmarks.json")}


@router.get("/system")
def system(db: Session = Depends(get_db)):
    db.execute(func.now() if not settings.database_url.startswith("sqlite") else func.date("now"))
    return {"database": "ok", "cache": "redis" if cache._redis else "in-memory", "artifacts": sorted(p.name for p in Path(settings.artifacts_dir).glob("*"))}
