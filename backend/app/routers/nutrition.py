from datetime import date
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import cache, models as m
from ..db import get_db
from ..security import current_user
from ..services import context as ctx, nlp, nutrition

router = APIRouter(tags=["nutrition"])
MEALS = "^(breakfast|lunch|dinner|snack)$"


@router.get("/foods/search")
def search(q: str = Query(min_length=2), limit: int = Query(10, le=30), db: Session = Depends(get_db)):
    key = f"food:{q.lower()}:{limit}"
    if (hit := cache.get(key)) is not None:
        return hit
    res = {"results": nutrition.search(db, q, limit), "per": "100 g", "source": "USDA FoodData Central"}
    cache.set(key, res, 3600)
    return res


@router.get("/foods/barcode/{code}")
def barcode(code: str):
    """Open Food Facts lookup (ODbL). Nothing is stored; credit Open Food Facts contributors where shown."""
    if not code.isdigit() or not 8 <= len(code) <= 14:
        raise HTTPException(422, "Barcode must be 8-14 digits")
    r = httpx.get(f"https://world.openfoodfacts.org/api/v2/product/{code}.json", params={"fields": "product_name,brands,nutriments"},
                  headers={"User-Agent": "V-E-L-D-O-R-A/1.0 (educational)"}, timeout=10)
    if r.status_code != 200 or r.json().get("status") != 1:
        raise HTTPException(404, "Product not found in Open Food Facts")
    p = r.json()["product"]; n = p.get("nutriments", {})
    return {"name": p.get("product_name"), "brand": p.get("brands"), "per": "100 g",
            "kcal": n.get("energy-kcal_100g"), "protein_g": n.get("proteins_100g"), "carb_g": n.get("carbohydrates_100g"),
            "fat_g": n.get("fat_100g"), "fiber_g": n.get("fiber_100g"), "source": "Open Food Facts (ODbL 1.0)", "url": "https://world.openfoodfacts.org/product/" + code}


class ParseIn(BaseModel):
    text: str = Field(min_length=2, max_length=500)
    meal: str | None = Field(None, pattern=MEALS)


@router.post("/nutrition/parse")
def parse(b: ParseIn, _=Depends(current_user), db: Session = Depends(get_db)):
    return nlp.analyse(db, b.text, b.meal)


class LogItem(BaseModel):
    fdc_id: int
    grams: float = Field(gt=0, le=5000)


class LogIn(BaseModel):
    meal: str = Field(pattern=MEALS)
    day: date | None = None
    items: list[LogItem] = Field(min_length=1, max_length=30)


@router.post("/nutrition/log", status_code=201)
def log(b: LogIn, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Persist items the user has confirmed (from /nutrition/parse or manual search)."""
    day = b.day or date.today()
    out = []
    for it in b.items:
        f = db.get(m.Food, it.fdc_id)
        if not f:
            raise HTTPException(404, f"Unknown food {it.fdc_id}")
        n = nutrition.nutrients(f, it.grams)
        db.add(m.FoodLog(user_id=u.id, day=day, meal=b.meal, fdc_id=f.fdc_id, description=f.description, grams=it.grams, kcal=n["kcal"],
                         protein_g=n["protein_g"], carb_g=n["carb_g"], fat_g=n["fat_g"], fiber_g=n["fiber_g"]))
        out.append({"description": f.description, **n})
    db.commit()
    from ..services import achievements
    return {"logged": out, "new_achievements": achievements.evaluate(db, u), "day_total": ctx.day_totals(db, u.id, day)}


@router.get("/nutrition/day")
def day_view(day: date | None = None, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    day = day or date.today()
    rows = db.query(m.FoodLog).filter_by(user_id=u.id, day=day).order_by(m.FoodLog.id).all()
    meals = {k: [] for k in ("breakfast", "lunch", "dinner", "snack")}
    for r in rows:
        meals[r.meal].append({"id": r.id, "description": r.description, "grams": r.grams, "kcal": r.kcal, "protein_g": r.protein_g,
                              "carb_g": r.carb_g, "fat_g": r.fat_g, "fiber_g": r.fiber_g})
    return {"day": str(day), "meals": meals, "total": ctx.day_totals(db, u.id, day), "targets": ctx.targets(u.profile)}


@router.delete("/nutrition/log/{log_id}", status_code=204)
def delete_log(log_id: int, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.query(m.FoodLog).filter_by(id=log_id, user_id=u.id).first()
    if not r:
        raise HTTPException(404, "Not found")
    db.delete(r); db.commit()
