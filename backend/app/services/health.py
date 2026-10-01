from datetime import date

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
KCAL_PER_KG = 7700  # widely used approximation; real change varies between people


def bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def bmi_category(v: float) -> str:
    return "underweight" if v < 18.5 else "normal" if v < 25 else "overweight" if v < 30 else "obesity"


def bmr(weight_kg, height_cm, age, sex) -> float:
    """Mifflin-St Jeor (1990)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + (5 if sex == "male" else -161), 0)


def tdee(bmr_v: float, activity: str) -> float:
    return round(bmr_v * ACTIVITY.get(activity, 1.375), 0)


def complete(p) -> bool:
    return all(getattr(p, k) for k in ("age", "sex", "height_cm", "weight_kg"))


def metrics(p) -> dict:
    b = bmi(p.weight_kg, p.height_cm)
    r = bmr(p.weight_kg, p.height_cm, p.age, p.sex)
    return {"bmi": b, "bmi_category": bmi_category(b), "bmr": r, "tdee": tdee(r, p.activity_level)}


def targets(p, conditions: set[str]) -> dict:
    """Daily calorie / macro / water targets plus the safety decisions taken. Safety rules always win."""
    m = metrics(p)
    notes, blocked = [], []
    kcal = m["tdee"]
    floor = 1500 if p.sex == "male" else 1200
    goal = p.goal_type
    if p.age is not None and p.age < 18:
        blocked.append("Calorie deficits and surplus plans are not generated for people under 18; please consult a clinician or dietitian.")
        goal = "maintain"
    if "underweight" in conditions and goal == "lose":
        notes.append("Weight-loss goal ignored because you selected 'underweight'. Targets are set to maintenance.")
        goal = "maintain"
    if goal in ("lose", "gain") and p.target_weight_kg and p.target_date:
        days = max((p.target_date - date.today()).days, 1)
        delta_kg = abs(p.target_weight_kg - p.weight_kg)
        weekly = delta_kg / (days / 7)
        cap = min(1.0, 0.01 * p.weight_kg) if goal == "lose" else 0.5
        if weekly > cap:
            notes.append(f"Your target date implies {weekly:.1f} kg/week; capped at {cap:.1f} kg/week for safety.")
            weekly = cap
        daily_delta = weekly * KCAL_PER_KG / 7
    else:
        weekly = 0.5 if goal in ("lose", "gain") and not blocked else 0
        daily_delta = weekly * KCAL_PER_KG / 7
    if goal == "lose":
        kcal = max(kcal - daily_delta, floor)
        if kcal == floor:
            notes.append(f"Calories held at the {floor} kcal safety floor.")
    elif goal == "gain":
        kcal = kcal + daily_delta
    kcal = round(kcal)
    protein_g = round(1.6 * p.weight_kg if goal != "maintain" else 1.2 * p.weight_kg)
    fat_g = round(0.27 * kcal / 9)
    carb_g = max(round((kcal - protein_g * 4 - fat_g * 9) / 4), 0)
    if "kidney_disease" in conditions:
        blocked.append("Kidney disease: protein, sodium, potassium and phosphorus limits are individual. Automatic meal plans are disabled; please follow your clinician's plan.")
    return {**m, "goal": goal, "kcal": kcal, "protein_g": protein_g, "carb_g": carb_g, "fat_g": fat_g, "fiber_g": round(14 * kcal / 1000),
            "water_ml": round(33 * p.weight_kg / 50) * 50, "weekly_change_kg": round(weekly, 2), "notes": notes, "blocked": blocked}
