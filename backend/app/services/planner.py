"""Diet + workout planners. Foods are always resolved from the nutrition DB; the lists below only name what to search for."""
import re
from sqlalchemy.orm import Session
from . import nutrition, rules
from .. import models as m

# role -> search phrases (resolved against USDA data; unresolved phrases are skipped)
POOL = {
    "breakfast": {
        "protein": ["egg whole cooked hard-boiled", "yogurt greek plain nonfat", "yogurt plain whole milk", "lentils cooked", "tofu"],
        "carb": ["oats whole grain rolled", "bread whole-wheat", "bread white"],
        "fruit": ["bananas ripe raw", "apples raw", "oranges raw", "blueberries raw"],
    },
    "main": {
        "protein": ["chicken breast boneless skinless cooked braised", "fish salmon atlantic raw", "lentils cooked boiled", "chickpeas cooked",
                    "fish tuna light canned water", "beef loin cooked", "tofu", "beans cannellini cooked"],
        "carb": ["rice white long-grain cooked", "potatoes russet raw", "potatoes sweet raw", "pasta cooked", "quinoa cooked", "bread whole-wheat"],
        "fat": ["almonds", "walnuts english", "oil olive", "peanut butter smooth"],
        "veg": ["broccoli raw", "spinach mature", "tomatoes raw", "carrots raw", "cabbage raw", "cucumber raw"],
    },
    "snack": {"fruit": ["apples raw", "bananas ripe raw", "oranges raw"], "protein": ["yogurt greek plain nonfat", "almonds"]},
}
SPLIT = {"breakfast": .25, "lunch": .32, "dinner": .33, "snack": .10}
ROLE_SHARE = {
    "breakfast": {"protein": .35, "carb": .40, "fruit": .25},
    "main": {"protein": .38, "carb": .40, "veg": .22},
    "snack": {"fruit": .55, "protein": .45},
}
GRAM_CAP = {"protein": 250, "carb": 300, "veg": 250, "fruit": 250, "fat": 30}
GLYC_SHARE = {"main": {"protein": .42, "carb": .20, "veg": .28, "fat": .10}, "breakfast": {"protein": .55, "carb": .25, "fruit": .20},
              "snack": {"protein": .65, "fruit": .35}}  # used when glycaemic rules apply
CAP_OVERRIDE = {"egg": 100, "oil": 15, "almond": 30, "yogurt": 250, "tofu": 200}


def _resolve(db: Session, phrase: str):
    hits = nutrition.search(db, phrase, limit=1)
    return db.get(m.Food, hits[0]["fdc_id"]) if hits else None


def _candidates(db, slot, role, banned, conditions):
    kind = "main" if slot in ("lunch", "dinner") else slot
    out, dropped = [], []
    for ph in POOL[kind].get(role, []):
        f = _resolve(db, ph)
        if not f:
            continue
        desc = f.description.lower()
        bad = next((f"{k} ({why})" for k, why in banned.items() if k in desc), None)
        if bad:
            dropped.append(f"{f.description}: excluded - {bad}")
            continue
        if conditions & rules.GLYCEMIC:
            carb_kcal_share = (f.carb_g or 0) * 4 / max(f.kcal, 1)
            if role == "protein" and carb_kcal_share > 0.45:
                dropped.append(f"{f.description}: skipped - carbohydrate-dense for a glycaemic-control plan")
                continue
            if role == "carb" and re.search(r"\bwhite\b|russet|pasta", desc):
                dropped.append(f"{f.description}: skipped - refined/high-glycaemic choice for a glycaemic-control plan")
                continue
        flags = rules.food_flags(conditions, f)
        if flags:
            dropped.append(f"{f.description}: skipped - {', '.join(flags)}")
            continue
        if f.fdc_id not in [o.fdc_id for o in out]:
            out.append(f)
    return out, dropped


def meal(db, slot, kcal, day_idx, banned, conditions, glyc):
    kind = "main" if slot in ("lunch", "dinner") else slot
    shares = dict(ROLE_SHARE[kind])
    if glyc:
        shares = dict(GLYC_SHARE[kind])
    items, notes = [], []
    for role, share in shares.items():
        cands, dropped = _candidates(db, slot, role, banned, conditions)
        notes += dropped
        if not cands:
            continue
        f = cands[(day_idx + (1 if slot == "dinner" else 0)) % len(cands)]
        cap = next((c for k, c in CAP_OVERRIDE.items() if k in f.description.lower()), GRAM_CAP.get(role, 250))
        grams = max(round(min(kcal * share / max(f.kcal, 1) * 100, cap) / 5) * 5, 10)
        items.append({"role": role, "fdc_id": f.fdc_id, "description": f.description, "_cap": cap, "_f": f, **nutrition.nutrients(f, grams)})
    have = sum(i["kcal"] for i in items)
    if items and have < 0.93 * kcal:  # top-up: grow items that still have headroom under their caps
        for _ in range(3):
            room = [i for i in items if i["grams"] < i["_cap"] * 1.0]
            if not room or sum(i["kcal"] for i in items) >= 0.97 * kcal:
                break
            need = kcal - sum(i["kcal"] for i in items)
            add = need / max(sum(i["kcal"] for i in room), 1)
            for i in room:
                g = min(round(i["grams"] * (1 + add) / 5) * 5, i["_cap"])
                i.update(nutrition.nutrients(i["_f"], g))
    for i in items:
        i.pop("_cap", None); i.pop("_f", None)
    tot = {k: round(sum(i[k] for i in items), 1) for k in ("kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "sodium_mg", "sat_fat_g")}
    return {"slot": slot, "items": items, "total": tot, "excluded": sorted(set(notes))}


def diet_plan(db: Session, tgt: dict, conditions: set[str], allergies, diets, days=1, start_idx=0) -> dict:
    banned = rules.excluded_keywords(conditions, allergies, diets)
    glyc = bool(conditions & rules.GLYCEMIC)
    plan_days = []
    for d in range(days):
        meals = [meal(db, s, tgt["kcal"] * SPLIT[s], start_idx + d, banned, conditions, glyc) for s in SPLIT]
        tot = {k: round(sum(x["total"][k] for x in meals), 1) for k in ("kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "sodium_mg", "sat_fat_g")}
        plan_days.append({"day": d + 1, "meals": meals, "total": tot, "vs_target_kcal": round(tot["kcal"] - tgt["kcal"])})
    why = [r for r in rules.nutrition_rules(conditions, tgt["kcal"])]
    checks = []
    for day in plan_days:
        t = day["total"]
        for r in why:
            if "carb_share_max" in r:
                share = t["carb_g"] * 4 / max(t["kcal"], 1)
                checks.append({"day": day["day"], "check": "carbohydrate share of energy", "limit": r["carb_share_max"], "actual": round(share, 2), "ok": share <= r["carb_share_max"] + .02})
            if "sodium_mg_max" in r:
                checks.append({"day": day["day"], "check": "sodium mg", "limit": r["sodium_mg_max"], "actual": t["sodium_mg"], "ok": t["sodium_mg"] <= r["sodium_mg_max"]})
            if "sat_fat_g_max" in r:
                checks.append({"day": day["day"], "check": "saturated fat g", "limit": r["sat_fat_g_max"], "actual": t["sat_fat_g"], "ok": t["sat_fat_g"] <= r["sat_fat_g_max"]})
    if banned:
        why.append({"condition": "exclusions", "rule": "Foods matching " + ", ".join(sorted(banned)) + " were removed",
                    "why": "Allergies, diet choices and intolerances you entered are hard filters."})
    warnings = []
    for day in plan_days:
        if day["total"]["kcal"] < 0.9 * tgt["kcal"]:
            warnings.append(f"Day {day['day']}: only {day['total']['kcal']} of {tgt['kcal']} kcal could be reached with the foods allowed by your profile; add foods you can eat or ask a dietitian.")
    bad = [c for c in checks if not c["ok"]]
    if bad:
        warnings.append(f"{len(bad)} rule check(s) were not met (see rule_checks). The plan is a starting point, not a guarantee.")
    return {"days": plan_days, "warnings": warnings, "targets": {k: tgt[k] for k in ("kcal", "protein_g", "carb_g", "fat_g", "fiber_g")}, "why": why, "rule_checks": checks,
            "method": "Rule-based selection from USDA FoodData Central rows; portions scaled to meal calorie share. Ingredients, not recipes.",
            "not_applied": ["budget (no price data in the approved datasets)"]}


# ------------------------------------------------------------------ workouts
EX = {  # name: (met_key, equipment, muscle, impact)
    "Bodyweight squat": ("strength_moderate", "none", "legs", "low"), "Push-up": ("strength_moderate", "none", "push", "low"),
    "Glute bridge": ("strength_moderate", "none", "legs", "low"), "Plank (seconds)": ("strength_moderate", "none", "core", "low"),
    "Inverted row (table)": ("strength_moderate", "none", "pull", "low"), "Lunge": ("strength_moderate", "none", "legs", "low"),
    "Dumbbell goblet squat": ("strength_moderate", "dumbbells", "legs", "low"), "Dumbbell bench press": ("strength_moderate", "dumbbells", "push", "low"),
    "Dumbbell row": ("strength_moderate", "dumbbells", "pull", "low"), "Dumbbell Romanian deadlift": ("strength_moderate", "dumbbells", "legs", "low"),
    "Dumbbell shoulder press": ("strength_moderate", "dumbbells", "push", "low"),
    "Barbell back squat": ("strength_vigorous", "gym", "legs", "low"), "Barbell bench press": ("strength_vigorous", "gym", "push", "low"),
    "Barbell row": ("strength_vigorous", "gym", "pull", "low"), "Deadlift": ("strength_vigorous", "gym", "legs", "low"),
    "Overhead press": ("strength_vigorous", "gym", "push", "low"), "Lat pulldown": ("strength_moderate", "gym", "pull", "low"),
}
CARDIO = {"low": ("walk_brisk", "Brisk walk"), "mid": ("cycle_moderate", "Cycling, steady"), "high": ("run_6mph", "Running intervals")}
LEVEL = {"beginner": dict(sets=2, reps=(10, 12), rpe=6, days=3), "intermediate": dict(sets=3, reps=(8, 12), rpe=7, days=4),
         "advanced": dict(sets=4, reps=(6, 10), rpe=8, days=5)}


def _kcal(met, kg, minutes):
    return round(met * kg * minutes / 60)


def workout_plan(db: Session, p, conditions: set[str], level: str, minutes: int, days: int | None, equipment: list[str]) -> dict:
    caps = rules.workout_rules(conditions, p.age)
    cfg = LEVEL[level]
    days = days or cfg["days"]
    rpe = min(cfg["rpe"], caps["max_rpe"])
    eq = {"none"} | set(equipment or [])
    if "gym" in eq:
        eq |= {"dumbbells"}
    pool = {k: v for k, v in EX.items() if v[1] in eq}
    if not caps["allow_max_effort"]:
        pool = {k: v for k, v in pool.items() if v[1] != "gym" or k in ("Lat pulldown",)}
        if not any(v[1] == "dumbbells" for v in pool.values()) and "dumbbells" in eq:
            pass
    mets = {a.key: a.met for a in db.query(m.MetActivity).all()}
    weight = p.weight_kg or 70
    goal = p.goal_type
    cardio_level = "low" if (rpe <= 5 or not caps["allow_hiit"]) else "mid" if rpe <= 7 else "high"
    cardio_key, cardio_name = CARDIO[cardio_level]
    split = [("Full body A", ["legs", "push", "pull", "core"]), ("Full body B", ["legs", "pull", "push", "core"])]
    sessions = []
    for d in range(days):
        name, groups = split[d % 2]
        strength_min = round(minutes * (0.7 if goal != "lose" else 0.55))
        cardio_min = minutes - strength_min
        exs, n_ex = [], max(3, min(6, strength_min // 8))
        for gi in range(n_ex):
            g = groups[gi % len(groups)]
            opts = [k for k, v in pool.items() if v[2] == g] or list(pool)
            ex = opts[(d + gi) % len(opts)]
            exs.append({"exercise": ex, "sets": cfg["sets"], "reps": "30-45 s" if "Plank" in ex else f"{cfg['reps'][0]}-{cfg['reps'][1]}",
                        "rest_s": 60 if level == "beginner" else 90, "target_rpe": rpe, "met_key": pool.get(ex, EX[ex])[0]})
        kc = _kcal(mets.get("strength_moderate", 3.5), weight, strength_min) + _kcal(mets.get(cardio_key, 4.3), weight, cardio_min)
        sessions.append({"day": d + 1, "focus": name, "strength_minutes": strength_min, "exercises": exs,
                         "cardio": {"activity": cardio_name, "met_key": cardio_key, "minutes": cardio_min}, "est_kcal": kc})
    progression = [{"week": w, "rule": r} for w, r in enumerate([
        "Learn the movements; finish every set with 2-3 reps left in reserve.",
        "Add 1-2 reps per set on every exercise.",
        "Add 1 set to the first two exercises of each session (or +2.5-5% load if you reach the top of the rep range).",
        "Deload: same exercises, 60% of the sets, then reassess."], 1)]
    return {"level": level, "days_per_week": days, "minutes": minutes, "sessions": sessions, "progressive_overload": progression,
            "safety": caps, "disclaimer_required": caps["clearance_required"],
            "kcal_method": "MET x body weight (kg) x hours, MET values from the Compendium seed table"}


def calories_for(db: Session, key: str, kg: float, minutes: float) -> tuple[float, float]:
    a = db.query(m.MetActivity).filter_by(key=key).one_or_none()
    if a is None:
        raise KeyError(key)
    return round(a.met * kg * minutes / 60, 1), a.met
