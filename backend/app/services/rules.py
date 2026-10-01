"""Rule engine. Rules always override ML and any personalised preference.

Thresholds are conventional public-health guidance values (e.g. sodium <= 2,300 mg/day, saturated fat <= ~6-10% of energy);
they are constraints for an informational tool, not clinical targets.
"""
CONDITIONS = {
    "type1_diabetes": "Type 1 Diabetes", "type2_diabetes": "Type 2 Diabetes", "prediabetes": "Prediabetes",
    "hypertension": "Hypertension", "hypotension": "Hypotension", "high_cholesterol": "High Cholesterol",
    "heart_disease": "Heart Disease", "obesity": "Obesity", "underweight": "Underweight", "fatty_liver": "Fatty Liver",
    "kidney_disease": "Kidney Disease", "thyroid": "Thyroid Disorder", "pcos": "PCOS", "anemia": "Anemia",
    "lactose_intolerance": "Lactose Intolerance", "gluten_intolerance": "Gluten Intolerance", "food_allergy": "Food Allergies",
}
GLYCEMIC = {"type1_diabetes", "type2_diabetes", "prediabetes", "pcos", "fatty_liver"}

ALLERGEN_KEYWORDS = {
    "peanut": ["peanut"], "tree_nut": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia", "brazil nut"],
    "milk": ["milk", "cheese", "yogurt", "yoghurt", "butter", "cream", "whey", "casein"], "egg": ["egg"],
    "soy": ["soy", "tofu", "edamame", "miso", "tempeh"], "wheat": ["wheat", "bread", "pasta", "flour", "bulgur", "couscous", "barley", "rye"],
    "fish": ["fish", "salmon", "tuna", "cod", "haddock", "pollock", "tilapia", "trout", "sardine", "mackerel"],
    "shellfish": ["shrimp", "crab", "lobster", "crayfish", "mollusk", "clam", "oyster", "mussel", "scallop"], "sesame": ["sesame", "tahini"],
}
DIET_EXCLUDE = {
    "vegetarian": ["chicken", "turkey", "beef", "pork", "lamb", "veal", "ham", "bacon", "sausage", "frankfurter", "fish", "salmon", "tuna", "shrimp", "crab"],
    "vegan": ["chicken", "turkey", "beef", "pork", "lamb", "veal", "ham", "bacon", "sausage", "frankfurter", "fish", "salmon", "tuna", "shrimp", "crab",
              "egg", "milk", "cheese", "yogurt", "butter", "cream", "honey", "whey"],
    "halal": ["pork", "ham", "bacon", "lard", "wine", "beer"], "pescatarian": ["chicken", "turkey", "beef", "pork", "lamb", "veal", "ham", "bacon"],
}
IMPLICIT = {"lactose_intolerance": ["milk", "cheese", "yogurt", "yoghurt", "cream", "whey"],
            "gluten_intolerance": ["wheat", "bread", "pasta", "flour", "barley", "rye", "couscous", "bulgur"]}


def excluded_keywords(conditions: set[str], allergies: list[str], diets: list[str]) -> dict[str, str]:
    """keyword -> reason"""
    out = {}
    for a in allergies:
        for k in ALLERGEN_KEYWORDS.get(a.lower().replace(" ", "_"), [a.lower()]):
            out[k] = f"allergy: {a}"
    for c in conditions:
        for k in IMPLICIT.get(c, []):
            out.setdefault(k, CONDITIONS[c])
    for d in diets:
        for k in DIET_EXCLUDE.get(d.lower(), []):
            out.setdefault(k, f"diet: {d}")
    return out


def food_flags(conditions: set[str], food) -> list[str]:
    """Per-100 g flags for a food given the user's conditions."""
    f = []
    sugar, sodium, sat = food.sugar_g or 0, food.sodium_mg or 0, food.sat_fat_g or 0
    if conditions & GLYCEMIC and sugar > 10:
        f.append(f"high sugar ({sugar:.0f} g/100 g)")
    if conditions & {"hypertension", "heart_disease", "kidney_disease"} and sodium > 400:
        f.append(f"high sodium ({sodium:.0f} mg/100 g)")
    if conditions & {"high_cholesterol", "heart_disease", "fatty_liver"} and sat > 5:
        f.append(f"high saturated fat ({sat:.1f} g/100 g)")
    return f


def nutrition_rules(conditions: set[str], kcal: int) -> list[dict]:
    r = []
    if conditions & GLYCEMIC:
        r.append({"condition": "glycaemic control", "rule": "Carbohydrates capped near 40% of energy, fibre-rich and low-sugar foods preferred",
                  "why": "Steadier carbohydrate intake and more fibre are standard dietary guidance for blood-glucose management.", "carb_share_max": 0.40})
    if conditions & {"hypertension", "heart_disease"}:
        r.append({"condition": "hypertension / heart", "rule": "Sodium limited to 2,300 mg/day; vegetables, fruit, whole grains and lean protein prioritised",
                  "why": "Lower sodium and a DASH-style pattern are standard dietary guidance for blood pressure.", "sodium_mg_max": 2300})
    if conditions & {"high_cholesterol", "heart_disease", "fatty_liver"}:
        r.append({"condition": "cholesterol / liver", "rule": "Saturated fat kept under ~7% of energy; oats, legumes, fish and fibre prioritised",
                  "why": "Replacing saturated fat with unsaturated fat and adding soluble fibre is standard dietary guidance for blood lipids.",
                  "sat_fat_g_max": round(0.07 * kcal / 9)})
    if "hypotension" in conditions:
        r.append({"condition": "hypotension", "rule": "No sodium restriction applied; regular meals and steady hydration encouraged",
                  "why": "Low blood pressure is not managed by the sodium limits used for hypertension."})
    if "anemia" in conditions:
        r.append({"condition": "anemia", "rule": "Varied protein and leafy vegetables included; iron needs are assessed by a clinician",
                  "why": "Iron values are not part of the loaded food table, so iron targets are not computed."})
    if "thyroid" in conditions:
        r.append({"condition": "thyroid", "rule": "Balanced, regular meals; no nutrient targets auto-generated",
                  "why": "Thyroid nutrition needs depend on diagnosis and medication timing, which only a clinician can advise on."})
    return r


def workout_rules(conditions: set[str], age: int | None) -> dict:
    """Return caps applied to any generated workout."""
    caps = {"max_rpe": 8, "allow_max_effort": True, "allow_hiit": True, "clearance_required": False, "notes": []}
    if conditions & {"heart_disease"}:
        caps.update(max_rpe=5, allow_max_effort=False, allow_hiit=False, clearance_required=True)
        caps["notes"].append("Heart disease: only light-to-moderate activity is suggested until a clinician clears your exercise plan.")
    if "hypertension" in conditions:
        caps.update(max_rpe=min(caps["max_rpe"], 6), allow_max_effort=False)
        caps["notes"].append("Hypertension: moderate effort, steady breathing, avoid maximal lifts and breath-holding.")
    if "hypotension" in conditions:
        caps["notes"].append("Hypotension: rise slowly between floor and standing exercises and stay hydrated.")
    if conditions & {"type1_diabetes", "type2_diabetes"}:
        caps["notes"].append("Diabetes: check with your care team about timing exercise around meals and medication.")
    if "obesity" in conditions:
        caps.update(allow_hiit=False)
        caps["notes"].append("Low-impact options are prioritised to protect joints.")
    if age is not None and age >= 65:
        caps.update(max_rpe=min(caps["max_rpe"], 7), allow_max_effort=False)
        caps["notes"].append("Age 65+: balance work is included and maximal efforts are avoided.")
    return caps
