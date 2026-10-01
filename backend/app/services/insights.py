"""Analytics + light ML on a user's own logs. Small-sample linear models with honest confidence labels.
(Random Forest / XGBoost need population data; the supplied population datasets are synthetic, so they are not used here.)"""
from datetime import date, timedelta
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LinearRegression
from ..config import settings


def _conf(n: int, r2: float) -> str:
    return "low" if n < 6 or r2 < 0.4 else "medium" if n < 14 or r2 < 0.7 else "high"


def weight_forecast(logs: list[tuple[date, float]], horizon_days: int = 28, target: float | None = None) -> dict:
    logs = sorted(logs)
    if len(logs) < 3:
        return {"available": False, "reason": "Log at least 3 weigh-ins (over 2+ days) to see a trend.", "n": len(logs)}
    d0 = logs[0][0]
    X = np.array([[(d - d0).days] for d, _ in logs], float)
    y = np.array([w for _, w in logs], float)
    if X.max() == 0:
        return {"available": False, "reason": "Weigh-ins need to span more than one day.", "n": len(logs)}
    mdl = LinearRegression().fit(X, y)
    r2 = float(mdl.score(X, y))
    resid = y - mdl.predict(X)
    sd = float(resid.std(ddof=2)) if len(y) > 2 else 0.0
    last = X.max()
    slope_week = float(mdl.coef_[0] * 7)
    pts = []
    for h in (7, 14, 28, horizon_days):
        x = last + h
        pred = float(mdl.predict([[x]])[0])
        pts.append({"days_ahead": h, "date": str(d0 + timedelta(days=int(x))), "predicted_kg": round(pred, 1),
                    "range_kg": [round(pred - 1.96 * sd * (1 + h / 30), 1), round(pred + 1.96 * sd * (1 + h / 30), 1)]})
    eta = None
    if target is not None and abs(mdl.coef_[0]) > 1e-4:
        days = (target - mdl.intercept_) / mdl.coef_[0]
        if days > last:
            eta = str(d0 + timedelta(days=int(days)))
    return {"available": True, "n": len(logs), "model": "LinearRegression", "slope_kg_per_week": round(slope_week, 2), "r2": round(r2, 2),
            "confidence": _conf(len(logs), r2), "forecast": pts, "goal_eta": eta,
            "caveat": "An estimate from your own recent trend; real results vary and this is not a guarantee."}


def consistency(day_set_food: set, day_set_workout: set, today: date, window: int = 14) -> dict:
    days = [today - timedelta(days=i) for i in range(window)]
    f = sum(d in day_set_food for d in days) / window
    w = sum(d in day_set_workout for d in days) / window
    # weighting is a product choice: logging meals matters most for tracking, workouts capped at 4/wk as "full credit"
    w_adj = min(w * 7 / 4, 1)
    score = round(100 * (0.6 * f + 0.4 * w_adj))
    streak = 0
    for d in days:
        if d in day_set_food or d in day_set_workout:
            streak += 1
        else:
            break
    return {"score": score, "meal_log_days": int(f * window), "workout_days": int(w * window), "window_days": window, "current_streak": streak,
            "method": "60% meal-logging days + 40% workout days (4 workouts/week = full credit) over the last 14 days"}


def nutrition_adherence(daily: dict[date, dict], target: dict) -> dict:
    if not daily:
        return {"available": False, "reason": "No meals logged yet."}
    within = [abs(v["kcal"] - target["kcal"]) <= 0.10 * target["kcal"] for v in daily.values()]
    prot = [v["protein_g"] >= 0.9 * target["protein_g"] for v in daily.values()]
    avg = {k: round(float(np.mean([v[k] for v in daily.values()])), 1) for k in ("kcal", "protein_g", "carb_g", "fat_g", "fiber_g")}
    return {"available": True, "days_logged": len(daily), "days_within_10pct_kcal": int(sum(within)), "days_protein_target_met": int(sum(prot)),
            "adherence_pct": round(100 * sum(within) / len(within)), "average_intake": avg,
            "note": "Days with partial logging look like under-eating; log every meal for a fair score."}


def behaviour_patterns(daily_kcal: dict[date, float]) -> list[str]:
    out = []
    wk = [v for d, v in daily_kcal.items() if d.weekday() < 5]
    we = [v for d, v in daily_kcal.items() if d.weekday() >= 5]
    if len(wk) >= 3 and len(we) >= 2:
        a, b = np.mean(wk), np.mean(we)
        if b > a * 1.12:
            out.append(f"Weekend intake averages {round(b - a)} kcal more than weekdays ({round(b)} vs {round(a)}).")
        elif b < a * 0.88:
            out.append(f"Weekend intake averages {round(a - b)} kcal less than weekdays.")
    return out


def sleep_insights(logs: list[dict]) -> dict:
    p = Path(settings.artifacts_dir) / "sleep_benchmarks.json"
    bench = json.loads(p.read_text()) if p.exists() else {}
    if not logs:
        return {"available": False, "reason": "No sleep logged yet."}
    hrs = float(np.mean([l["hours"] for l in logs])); q = float(np.mean([l["quality"] for l in logs]))
    msgs = [f"Average sleep over {len(logs)} night(s): {hrs:.1f} h, self-rated quality {q:.1f}/10."]
    pct = bench.get("sleep_hours_percentiles")
    if pct:
        med = pct["0.5"]
        msgs.append(f"The reference sample (374 adults, a synthetic dataset) has a median of {med} h; yours is {'above' if hrs > med else 'below' if hrs < med else 'at'} that.")
    if hrs < 7:
        msgs.append("Many adult guidelines suggest 7 or more hours; this is descriptive, not a diagnosis.")
    if len(logs) >= 4:
        x = np.array([l["hours"] for l in logs]); y = np.array([l["quality"] for l in logs])
        if x.std() > 0 and y.std() > 0:
            r = float(np.corrcoef(x, y)[0, 1])
            msgs.append(f"In your own logs, longer nights go with {'better' if r > 0.3 else 'no clearly better' if r > -0.3 else 'worse'} self-rated quality (r={r:.2f}, n={len(logs)}).")
    return {"available": True, "avg_hours": round(hrs, 1), "avg_quality": round(q, 1), "messages": msgs}
