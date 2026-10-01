import re
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import models as m

_STOP = {"raw", "the", "a", "an", "of", "with", "and", "in", "or", "fresh"}
_CACHE: dict = {"rows": None}
# Only words that change the *search phrase*. No nutrition values live here.
ALIASES = {
    "egg": "egg whole", "eggs": "egg whole", "curd": "yogurt", "yoghurt": "yogurt", "oatmeal": "oats rolled", "porridge": "oats rolled",
    "chicken": "chicken breast", "rice": "rice white cooked", "bread": "bread white", "milk": "milk whole",
    "potatoes": "potato", "tomatoes": "tomato", "salmon": "fish salmon", "tuna": "fish tuna", "lentils": "lentils cooked",
    "beans": "beans", "chickpeas": "chickpeas", "pasta": "pasta cooked", "oats": "oats rolled",
}
# USDA standard single-item weights (g) used ONLY when the user gives a count with no unit and the food has no portion row.
# They are flagged "assumed" in the API so the user confirms them. Verify against USDA SR Legacy household measures.
PIECE_G = {"egg": 50, "banana": 118, "apple": 182, "orange": 131, "tomato": 123, "potato": 173}


def stem(w: str) -> str:
    w = w.lower()
    for suf, rep in (("ies", "y"), ("oes", "o"), ("ches", "ch"), ("es", "e"), ("s", "")):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[: -len(suf)] + rep
    return w


def tokens(s: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[a-zA-Z]+", s) if t.lower() not in _STOP]


def _load(db: Session):
    if _CACHE["rows"] is None:
        rows = db.execute(select(m.Food)).scalars().all()
        _CACHE["rows"] = [(f, tokens(f.description)) for f in rows]
    return _CACHE["rows"]


def reset_cache():
    _CACHE["rows"] = None


_PENALTY = {"flour": .25, "dried": .15, "powder": .25, "frozen": .05, "restaurant": .15, "babyfood": .4, "juice": .1, "canned": .05,
            "oil": .05, "snacks": .2, "overripe": .1, "duck": .2, "goose": .2, "quail": .2, "buttermilk": .2, "fast": .2, "cookies": .2, "cereal": .1}


def search(db: Session, query: str, limit: int = 8, cooked_hint: bool | None = None) -> list[dict]:
    q = query.strip().lower()
    phrase = ALIASES.get(q, q)
    qt = tokens(phrase)
    if not qt:
        return []
    out = []
    for f, dt in _load(db):
        if not dt:
            continue
        hit = 0.0
        for t in qt:
            if t in dt:
                hit += 1
            else:
                best = max((fuzz.ratio(t, d) for d in dt), default=0)
                hit += 0.8 if best >= 88 else 0
        if hit == 0:
            continue
        coverage = hit / len(qt)
        precision = min(hit, len(dt)) / len(dt)
        score = 0.75 * coverage + 0.25 * precision
        first = 0.08 if dt[0] == qt[0] else 0
        pen = sum(v for k, v in _PENALTY.items() if k in f.description.lower() and k not in q)
        cook = 0
        if cooked_hint is True and re.search(r"cooked|boiled|roasted|baked", f.description, re.I):
            cook = 0.1
        if cooked_hint is False and re.search(r"\braw\b", f.description, re.I):
            cook = 0.1
        out.append((score + first + cook - pen, f))
    out.sort(key=lambda x: (-x[0], len(x[1].description)))
    return [{"fdc_id": f.fdc_id, "description": f.description, "category": f.category, "score": round(s, 3), "kcal_per_100g": round(f.kcal, 1)}
            for s, f in out[:limit] if s > 0.3]


def nutrients(food: m.Food, grams: float) -> dict:
    k = grams / 100
    g = lambda v: round(max(v or 0, 0) * k, 1)
    return {"grams": round(grams, 1), "kcal": round(food.kcal * k), "protein_g": g(food.protein_g), "carb_g": g(food.carb_g),
            "fat_g": g(food.fat_g), "fiber_g": g(food.fiber_g), "sugar_g": g(food.sugar_g), "sodium_mg": round((food.sodium_mg or 0) * k),
            "sat_fat_g": g(food.sat_fat_g)}


def grams_for(db: Session, food: m.Food, qty: float, unit: str | None) -> tuple[float | None, str | None]:
    """Return (grams, basis) where basis says how the weight was derived."""
    weight = {"g": 1, "gram": 1, "grams": 1, "kg": 1000, "oz": 28.3495, "ounce": 28.3495, "lb": 453.592, "pound": 453.592,
              "ml": 1, "l": 1000}
    if unit in weight:
        return qty * weight[unit] if unit not in ("ml", "l") else qty * weight[unit], "explicit weight" if unit not in ("ml", "l") else "assumes 1 ml = 1 g"
    portions = db.execute(select(m.FoodPortion).where(m.FoodPortion.fdc_id == food.fdc_id)).scalars().all()
    if unit:
        u = stem(unit)
        for p in portions:
            if u and u in tokens(p.unit_label):
                return qty * p.gram_weight / p.amount, f"USDA portion: {p.amount:g} {p.unit_label} = {p.gram_weight:g} g"
        return None, None
    if portions:  # a bare count: use a countable portion
        for p in portions:
            if p.unit_label.lower() not in ("cup", "fl oz", "quart", "tablespoon", "teaspoon", "drained", "chopped"):
                return qty * p.gram_weight / p.amount, f"USDA portion: {p.amount:g} {p.unit_label} = {p.gram_weight:g} g"
    for k, g in PIECE_G.items():
        if k in food.description.lower():
            return qty * g, f"assumed {g} g per {k} (USDA standard size) - please confirm"
    return None, None
