"""Natural-language food logging: text -> items -> DB lookup -> estimate -> user confirmation.
Rule-based parser (no model) so every number traces to a dataset row. Always returns needs_confirmation=True."""
import re
from sqlalchemy.orm import Session
from . import nutrition
from .. import models as m

WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "half": 0.5, "couple": 2, "dozen": 12}
UNITS = r"(?:kg|g|gm|grams?|oz|ounces?|lbs?|pounds?|ml|l|cups?|tbsp|tablespoons?|tsp|teaspoons?|slices?|pieces?|glass(?:es)?|bowls?|servings?)"
UNIT_CANON = {"gm": "g", "grams": "g", "gram": "g", "lbs": "lb", "ounces": "oz", "ounce": "oz", "pounds": "lb", "pound": "lb",
              "glasses": "glass", "slices": "slice", "pieces": "piece", "bowls": "bowl", "servings": "serving", "tablespoons": "tablespoon", "tbsp": "tablespoon", "teaspoons": "teaspoon", "tsp": "teaspoon", "cups": "cup"}
FILLER = r"^(?:i\s+)?(?:just\s+)?(?:ate|had|eaten|consumed|drank|have|for (?:breakfast|lunch|dinner)[, ]*(?:i\s+had)?)\s+"
COOKED = re.compile(r"\b(cooked|boiled|fried|grilled|roasted|baked|steamed)\b", re.I)


def split_items(text: str) -> list[str]:
    t = re.sub(FILLER, "", text.strip().lower()).strip(" .")
    return [p.strip() for p in re.split(r",|;|&|\band\b|\bwith\b|\bplus\b|\balong with\b", t) if p.strip()]


def parse_item(part: str) -> dict:
    s = part.strip()
    qty, unit = 1.0, None
    mt = re.match(rf"^(\d+(?:\.\d+)?(?:\s*/\s*\d+)?|{'|'.join(WORDS)})\s*(?:({UNITS})\b)?\s*(?:of\s+)?(.*)$", s)
    explicit = False
    if mt:
        raw_q, unit, rest = mt.group(1), mt.group(2), mt.group(3)
        if raw_q in WORDS:
            qty = WORDS[raw_q]
        elif "/" in raw_q:
            a, b = re.split(r"\s*/\s*", raw_q)
            qty = float(a) / float(b)
        else:
            qty = float(raw_q)
        explicit = True
        s = rest
    else:  # "150g" glued or "chicken 150g"
        mg = re.match(rf"^(\d+(?:\.\d+)?)({UNITS})\b\s*(.*)$", s)
        if mg:
            qty, unit, s, explicit = float(mg.group(1)), mg.group(2), mg.group(3), True
    unit = UNIT_CANON.get(unit, unit) if unit else None
    return {"raw": part.strip(), "quantity": qty, "unit": unit, "food_query": s.strip(), "quantity_given": explicit}


def analyse(db: Session, text: str, meal: str | None = None) -> dict:
    items = []
    for part in split_items(text):
        it = parse_item(part)
        q = it["food_query"]
        cooked = True if COOKED.search(q) else None
        q_clean = COOKED.sub("", q).strip()
        cands = nutrition.search(db, q_clean, limit=5, cooked_hint=cooked)
        it["candidates"] = cands
        it["selected"] = None
        it["issues"] = []
        if not cands:
            it["issues"].append("No matching food in the approved datasets - search manually or add grams for a different food.")
        else:
            food = db.get(m.Food, cands[0]["fdc_id"])
            grams, basis = nutrition.grams_for(db, food, it["quantity"], it["unit"])
            it["selected"] = {"fdc_id": food.fdc_id, "description": food.description, "source": food.source}
            if grams is None:
                it["issues"].append("Amount needed: tell me the weight in grams (no household measure is available for this food).")
            else:
                it["selected"]["estimate"] = nutrition.nutrients(food, grams)
                it["selected"]["basis"] = basis
                if basis and basis.startswith("assumed"):
                    it["issues"].append(basis)
            if not it["quantity_given"]:
                it["issues"].append("No quantity given: assumed 1.")
            if len(cands) > 1 and cands[1]["score"] >= cands[0]["score"] - 0.05:
                it["issues"].append("Several close matches - pick the right one.")
        items.append(it)
    ok = [i for i in items if i["selected"] and "estimate" in i["selected"]]
    total = {k: round(sum(i["selected"]["estimate"][k] for i in ok), 1) for k in ("kcal", "protein_g", "carb_g", "fat_g", "fiber_g")} if ok else {}
    return {"input": text, "meal": meal, "items": items, "total": total, "needs_confirmation": True,
            "message": "Estimates come from USDA FoodData Central values. Please confirm or correct each item before it is logged."}
