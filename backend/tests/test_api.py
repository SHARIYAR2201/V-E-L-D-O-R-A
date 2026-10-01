from datetime import date, timedelta
from conftest import signup
from app import mailer


def test_auth_flow(client):
    h = signup(client, "a1@example.com")
    assert client.get("/api/me", headers=h).json()["email"] == "a1@example.com"
    assert client.post("/api/auth/register", json={"email": "a1@example.com", "password": "correct-horse-1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a1@example.com", "password": "wrong-password"}).status_code == 401
    tok = client.post("/api/auth/login", json={"email": "a1@example.com", "password": "correct-horse-1"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    assert client.post("/api/auth/logout", headers=H).status_code == 204
    assert client.get("/api/me", headers=H).status_code == 401  # revoked
    assert client.get("/api/me").status_code == 401


def test_email_verify_and_reset(client):
    signup(client, "a2@example.com")
    tok = [x for x in mailer.OUTBOX if x["to"] == "a2@example.com"][-1]["body"].split(": ")[1]
    assert client.post("/api/auth/verify-email", json={"token": tok}).json()["verified"]
    assert client.post("/api/auth/verify-email", json={"token": tok}).status_code == 400  # single use
    client.post("/api/auth/forgot-password", json={"email": "a2@example.com"})
    rt = [x for x in mailer.OUTBOX if x["subject"].startswith("Reset")][-1]["body"].split(": ")[1]
    assert client.post("/api/auth/reset-password", json={"token": rt, "new_password": "brand-new-pass-2"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "a2@example.com", "password": "brand-new-pass-2"}).status_code == 200
    assert client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}).status_code == 200  # no enumeration


def test_metrics(client, user):
    r = client.get("/api/me/metrics", headers=user).json()
    assert r["current"]["bmi"] == 27.8 and r["current"]["bmr"] == 1828  # Mifflin-St Jeor, male 34y 178cm 88kg
    assert r["current"]["tdee"] == round(1828 * 1.55)
    assert 1500 <= r["targets"]["kcal"] < r["current"]["tdee"]  # deficit with safety floor


def test_safety_rules(client, user):
    client.put("/api/me/profile", headers=user, json={"age": 16})
    assert client.get("/api/plans/diet", headers=user).json()["blocked"]
    client.put("/api/me/profile", headers=user, json={"age": 40, "conditions": ["kidney_disease"]})
    assert client.get("/api/plans/diet", headers=user).json()["blocked"]
    assert client.put("/api/me/profile", headers=user, json={"conditions": ["made_up"]}).status_code == 422


def test_nlp_log_flow(client, user):
    r = client.post("/api/nutrition/parse", headers=user, json={"text": "I ate 2 eggs and 150g chicken"}).json()
    assert r["needs_confirmation"] and len(r["items"]) == 2
    chk = r["items"][1]["selected"]
    assert r["items"][1]["quantity"] == 150 and chk["estimate"]["grams"] == 150
    assert chk["estimate"]["kcal"] > 100
    lg = client.post("/api/nutrition/log", headers=user, json={"meal": "lunch", "items": [{"fdc_id": chk["fdc_id"], "grams": 150}]}).json()
    assert lg["day_total"]["kcal"] == chk["estimate"]["kcal"] and "first_meal" in lg["new_achievements"]
    assert client.post("/api/nutrition/parse", headers=user, json={"text": "3 dragonfruit"}).json()["items"][0]["issues"]  # never invents


def test_allergy_and_diet_filters(client, user):
    client.put("/api/me/profile", headers=user, json={"allergies": ["egg", "milk"], "diet_preferences": ["vegetarian"], "conditions": ["hypertension"]})
    plan = client.get("/api/plans/diet?days=3", headers=user).json()
    for d in plan["days"]:
        for mm in d["meals"]:
            for it in mm["items"]:
                low = it["description"].lower()
                assert not any(k in low for k in ("egg", "milk", "yogurt", "chicken", "beef", "fish")), low
    assert any("sodium" in c["check"] for c in plan["rule_checks"]) and plan["why"]


def test_workout_safety_and_calories(client, user):
    client.put("/api/me/profile", headers=user, json={"conditions": ["heart_disease"]})
    w = client.post("/api/plans/workout", headers=user, json={"level": "advanced", "minutes": 45}).json()
    assert w["safety"]["clearance_required"] and all(e["target_rpe"] <= 5 for s in w["sessions"] for e in s["exercises"])
    r = client.post("/api/workouts", headers=user, json={"activity_key": "run_6mph", "minutes": 30}).json()
    assert r["kcal_burned"] == round(9.8 * 88 * 0.5, 1)
    assert client.post("/api/workouts", headers=user, json={"activity_key": "nope", "minutes": 30}).status_code == 404


def test_sleep_water_weight_insights(client, user):
    assert client.post("/api/sleep", headers=user, json={"bedtime": "23:30", "wake_time": "06:30", "quality": 7}).json()["hours"] == 7.0
    assert client.post("/api/water", headers=user, json={"ml": 500}).json()["total_ml"] == 500
    for i, w in enumerate([88, 87.6, 87.3, 86.9, 86.6]):
        client.post("/api/weight", headers=user, json={"weight_kg": w, "day": str(date.today() - timedelta(days=(4 - i) * 3))})
    ins = client.get("/api/ai/insights", headers=user).json()["weight_trend"]
    assert ins["available"] and ins["slope_kg_per_week"] < 0 and ins["confidence"] in ("low", "medium", "high")
    assert "not a guarantee" in ins["caveat"]


def test_assistant(client, user):
    a = client.post("/api/ai/assistant", headers=user, json={"message": "I have 500 calories left, what should I eat?"}).json()
    assert a["intent"] == "meal_suggestion" and all(i["kcal"] <= 500 for i in a["data"]["ideas"])
    assert any("informational" in d for d in a["disclaimers"])


def test_admin_guard_and_attribution(client, user):
    assert client.get("/api/admin/stats", headers=user).status_code == 403
    boss = signup(client, "boss@example.com")
    assert client.get("/api/admin/stats", headers=boss).json()["foods_in_db"] > 1000
    d = client.get("/api/meta/datasets").json()
    assert len(d["datasets"]) >= 10 and all("citation" in x and "license" in x for x in d["datasets"])
