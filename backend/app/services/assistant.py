"""Contextual assistant. Deterministic and grounded: every number comes from the user's logs or the food database.
An LLM can be layered on top by passing `reply` + `context` to a provider; the rules/safety output below stays authoritative."""
import re
from datetime import date, timedelta
from sqlalchemy.orm import Session
from .. import models as m
from . import context as ctx, insights, nutrition, planner, rules
from ..disclaimers import DISCLAIMERS


def _snack_ideas(db, budget_kcal, conditions, allergies, diets):
    banned = rules.excluded_keywords(conditions, allergies, diets)
    out = []
    for slot, role in (("snack", "fruit"), ("snack", "protein"), ("lunch", "protein"), ("lunch", "veg"), ("lunch", "carb")):
        cands, _ = planner._candidates(db, slot, role, banned, conditions)
        for f in cands:
            grams = min(100 * budget_kcal * 0.6 / max(f.kcal, 1), 250)
            n = nutrition.nutrients(f, round(grams / 10) * 10 or 10)
            if n["kcal"] <= budget_kcal:
                out.append({"description": f.description, **n})
    out.sort(key=lambda x: -x["protein_g"])
    return out[:4]


def answer(db: Session, user: m.User, text: str) -> dict:
    p = user.profile
    t = text.lower()
    today = date.today()
    tg = ctx.targets(p)
    conds = ctx.cond_set(p)
    if tg is None:
        return {"reply": "Complete your profile (age, sex, height, weight) so I can work from your targets.", "intent": "profile_incomplete", "disclaimers": DISCLAIMERS[:1]}
    eaten = ctx.day_totals(db, user.id, today)
    left = round(tg["kcal"] - eaten["kcal"])
    m_left = re.search(r"(\d{2,4})\s*(?:k?cal|calories)", t)
    why, data, intent = [], {}, "general"

    if any(w in t for w in ("eat", "dinner", "lunch", "snack", "hungry", "calories left", "cal left")) or m_left:
        intent = "meal_suggestion"
        budget = int(m_left.group(1)) if m_left else max(left, 0)
        if budget < 60:
            reply = "You are at or near your calorie target for today. If you are still hungry, water or vegetables are low-calorie options."
        else:
            ideas = _snack_ideas(db, budget, conds, p.allergies or [], p.diet_preferences or [])
            data["ideas"] = ideas
            names = "; ".join(f"{i['grams']:.0f} g {i['description'].split(',')[0].lower()} ({i['kcal']} kcal, {i['protein_g']} g protein)" for i in ideas[:3])
            reply = f"With about {budget} kcal available, options that fit are: {names}." if ideas else "I could not find foods that fit both your budget and your restrictions."
            why.append(f"Budget = {'the amount you gave' if m_left else f'daily target {tg['kcal']} minus {eaten['kcal']:.0f} logged'}; ranked by protein.")
            if p.allergies or p.diet_preferences or conds:
                why.append("Your allergies, diet choices and health-condition rules were applied before ranking.")
    elif any(w in t for w in ("progress", "how am i", "doing")):
        intent = "progress"
        wl = [(r.day, r.weight_kg) for r in db.query(m.WeightLog).filter_by(user_id=user.id)]
        f = insights.weight_forecast(wl, target=p.target_weight_kg)
        cons = insights.consistency({d for d in ctx.daily_food(db, user.id)}, {r[0] for r in db.query(m.WorkoutLog.day).filter_by(user_id=user.id)}, today)
        data = {"forecast": f, "consistency": cons}
        reply = f"Consistency score {cons['score']}/100 (current streak {cons['current_streak']} day(s)). "
        reply += (f"Your weight trend is {f['slope_kg_per_week']:+.2f} kg/week ({f['confidence']} confidence, {f['n']} weigh-ins)." if f["available"] else f["reason"])
    elif any(w in t for w in ("workout", "exercise", "train", "gym")):
        intent = "workout"
        wp = planner.workout_plan(db, p, conds, p.experience if p.experience in planner.LEVEL else "beginner", 40, 3, p.equipment or [])
        s = wp["sessions"][(today.toordinal()) % len(wp["sessions"])]
        data = {"session": s, "safety": wp["safety"]}
        lst = ", ".join(f"{e['exercise']} {e['sets']}x{e['reps']}" for e in s["exercises"])
        reply = f"Today: {s['focus']} - {lst}, then {s['cardio']['minutes']} min {s['cardio']['activity'].lower()} (about {s['est_kcal']} kcal)."
        why += wp["safety"]["notes"]
    elif "sleep" in t:
        intent = "sleep"
        logs = [{"hours": r.hours, "quality": r.quality} for r in db.query(m.SleepLog).filter(m.SleepLog.user_id == user.id, m.SleepLog.day >= today - timedelta(days=14))]
        si = insights.sleep_insights(logs)
        reply = " ".join(si["messages"]) if si["available"] else si["reason"]
    elif "water" in t or "hydrat" in t:
        intent = "hydration"
        ml = ctx.water(db, user.id, today)
        reply = f"You have logged {ml:.0f} ml of your {tg['water_ml']} ml goal today ({round(100 * ml / tg['water_ml'])}%)."
    else:
        reply = (f"Today you have logged {eaten['kcal']:.0f} of {tg['kcal']} kcal ({left} left). Ask me what to eat, how your progress looks, "
                 "what workout to do, or about sleep and water.")
    return {"reply": reply, "intent": intent, "why": why, "data": data, "targets": {k: tg[k] for k in ("kcal", "protein_g", "carb_g", "fat_g")},
            "eaten_today": eaten, "disclaimers": DISCLAIMERS[:1] + DISCLAIMERS[3:]}
