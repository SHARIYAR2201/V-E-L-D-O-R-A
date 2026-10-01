"""Train the dataset-backed models and write artifacts + honest metrics.

    python -m scripts.train

exercise_dataset.csv                 -> calorie-burn regressor
diabetes_risk_prediction_dataset.csv -> lifestyle risk-indicator classifier (NOT a diagnostic tool)
Sleep_health_and_lifestyle_dataset   -> sleep-quality linear model + population benchmarks
survey_605.csv                       -> wearable-engagement summary used for product/notification design
"""
import json
from pathlib import Path
import joblib, numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor
from app.config import settings

RAW = Path(settings.data_dir) / "raw"
OUT = Path(settings.artifacts_dir); OUT.mkdir(exist_ok=True)
SEED = 42
metrics: dict = {}


def prep(num, cat, scale=False):
    n = [("imp", SimpleImputer(strategy="median"))] + ([("sc", StandardScaler())] if scale else [])
    return ColumnTransformer([("n", Pipeline(n), num),
                              ("c", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                              ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat)])


# ---------------------------------------------------------------- calorie burn
def train_calories():
    df = pd.read_csv(RAW / "exercise_dataset.csv")
    num = ["Duration", "Heart Rate", "Actual Weight", "Age", "Exercise Intensity", "BMI"]
    cat = ["Gender", "Exercise"]
    X, y = df[num + cat], df["Calories Burn"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED)
    cands = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(300, min_samples_leaf=3, random_state=SEED, n_jobs=-1),
        "XGBoost": XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9, random_state=SEED),
    }
    res, best, best_r2 = {}, None, -9
    for k, mdl in cands.items():
        p = Pipeline([("pre", prep(num, cat, scale=True)), ("m", mdl)]).fit(Xtr, ytr)
        pr = p.predict(Xte)
        res[k] = {"r2": round(r2_score(yte, pr), 4), "mae_kcal": round(mean_absolute_error(yte, pr), 2)}
        if res[k]["r2"] > best_r2:
            best, best_r2, best_name = p, res[k]["r2"], k
    corr = df[num + ["Calories Burn"]].corr()["Calories Burn"].drop("Calories Burn").abs().round(3).to_dict()
    metrics["calorie_burn"] = {"rows": len(df), "holdout": "20%", "candidates": res, "best_candidate": best_name,
                               "target_mean_kcal": round(float(y.mean()), 1), "abs_corr_with_target": corr,
                               "deployed": False,
                               "finding": "Holdout R2 <= 0 for every model and |corr| with the target is ~0 for every feature: the file carries no "
                                          "learnable signal, so calorie burn in the app uses MET x weight x time instead.",
                               "note": "Exercise names in the source file are anonymised (Exercise 1-10)."}


# ---------------------------------------------------------------- lifestyle risk indicator
LEAK = ["Patient_ID", "Diabetes_Risk_Score", "AI_Health_Recommendation", "Doctor_Consultation_Needed"]
LIFESTYLE_NUM = ["Age", "BMI", "Waist_Circumference_cm", "Exercise_Hours_Per_Week", "Daily_Walking_Minutes", "Sleep_Hours", "Daily_Water_Intake_L"]
LIFESTYLE_CAT = ["Gender", "Physical_Activity_Level", "Diet_Quality", "Sugar_Intake_Level", "Stress_Level", "Smoking_Status",
                 "Alcohol_Consumption", "Family_History_Diabetes", "Hypertension"]


def train_risk():
    df = pd.read_csv(RAW / "diabetes_risk_prediction_dataset.csv")
    audit = {"rows": len(df), "missing_cells": int(df.isna().sum().sum()), "class_counts": df.Diabetes_Risk.value_counts().to_dict()}
    # leakage / label-quality audit: how well do the excluded columns alone explain the label?
    audit["corr_score_vs_label_rank"] = round(float(df.Diabetes_Risk_Score.corr(df.Diabetes_Risk.map({"Low": 0, "Moderate": 1, "High": 2}))), 3)
    audit["bmi_height_weight_consistency_median_abs_err"] = round(float(((df.Weight_kg / (df.Height_cm / 100) ** 2) - df.BMI).abs().median()), 2)
    df = df.dropna(subset=["Diabetes_Risk"])
    classes = ["Low", "Moderate", "High"]
    y = df.Diabetes_Risk.map({c: i for i, c in enumerate(classes)})
    X = df[LIFESTYLE_NUM + LIFESTYLE_CAT]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    w = ytr.map(len(ytr) / (3 * ytr.value_counts())).values  # balanced sample weights
    cands = {
        "LogisticRegression": Pipeline([("pre", prep(LIFESTYLE_NUM, LIFESTYLE_CAT, True)), ("m", LogisticRegression(max_iter=2000, class_weight="balanced"))]),
        "RandomForest": Pipeline([("pre", prep(LIFESTYLE_NUM, LIFESTYLE_CAT)), ("m", RandomForestClassifier(300, min_samples_leaf=5, class_weight="balanced", random_state=SEED, n_jobs=-1))]),
        "XGBoost": Pipeline([("pre", prep(LIFESTYLE_NUM, LIFESTYLE_CAT)), ("m", XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, random_state=SEED))]),
    }
    res, best, best_f1 = {}, None, -1
    for k, p in cands.items():
        p.fit(Xtr, ytr, **({"m__sample_weight": w} if k == "XGBoost" else {}))
        pr = p.predict(Xte)
        f1 = f1_score(yte, pr, average="macro")
        res[k] = {"accuracy": round(accuracy_score(yte, pr), 4), "balanced_accuracy": round(balanced_accuracy_score(yte, pr), 4), "macro_f1": round(f1, 4)}
        if f1 > best_f1:
            best, best_f1, best_name = p, f1, k
    majority = round(float((yte == yte.mode()[0]).mean()), 4)
    rep = classification_report(yte, best.predict(Xte), target_names=classes, output_dict=True, zero_division=0)
    metrics["lifestyle_risk_indicator"] = {"audit": audit, "features": LIFESTYLE_NUM + LIFESTYLE_CAT, "excluded_as_leakage": LEAK,
                                           "excluded_clinical_labs": ["Blood_Glucose", "HbA1c", "Fasting_Blood_Sugar", "Insulin_Level"],
                                           "candidates": res, "best_candidate": best_name, "majority_class_baseline_accuracy": majority, "deployed": False,
                                           "finding": "Lifestyle features barely beat the majority-class baseline and the Low class is never recovered, so no "
                                                      "risk score is shown to users. The labels appear to be derived from lab values that the app does not collect.",
                                           "per_class_f1": {c: round(rep[c]["f1-score"], 3) for c in classes},
                                           "caveat": "Dataset labels look synthetic; output is an informational lifestyle indicator, never a diagnosis."}


# ---------------------------------------------------------------- sleep
def train_sleep():
    df = pd.read_csv(RAW / "Sleep_health_and_lifestyle_dataset.csv")
    feats = ["Sleep Duration", "Stress Level", "Physical Activity Level", "Daily Steps", "Age"]
    X, y = df[feats], df["Quality of Sleep"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED)
    lr = Pipeline([("sc", StandardScaler()), ("m", LinearRegression())]).fit(Xtr, ytr)
    r2 = r2_score(yte, lr.predict(Xte)); mae = mean_absolute_error(yte, lr.predict(Xte))
    lr.fit(X, y)
    coefs = dict(zip(feats, lr.named_steps["m"].coef_.round(3).tolist()))
    bins = pd.cut(df.Age, [0, 29, 39, 49, 120], labels=["<30", "30-39", "40-49", "50+"])
    bench = {
        "rows": len(df),
        "sleep_hours_percentiles": {str(q): float(df["Sleep Duration"].quantile(q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
        "quality_by_age_band": df.groupby(bins, observed=True)["Quality of Sleep"].mean().round(2).to_dict(),
    }
    bench["quality_by_age_band"] = {str(k): v for k, v in bench["quality_by_age_band"].items()}
    joblib.dump({"model": lr, "features": feats}, OUT / "sleep_model.joblib")
    (OUT / "sleep_benchmarks.json").write_text(json.dumps(bench, indent=2))
    metrics["sleep_quality"] = {"rows": len(df), "features": feats, "holdout_r2": round(r2, 4), "holdout_mae": round(mae, 3),
                                "standardised_coefficients": coefs, "model": "LinearRegression (descriptive, not diagnostic)"}


# ---------------------------------------------------------------- survey
def summarise_survey():
    df = pd.read_csv(RAW / "survey_605.csv", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    def share(col, vals):
        s = df[col].dropna()
        return round(float(s.isin(vals).mean()), 3) if len(s) else None
    cols = {c: c for c in df.columns}
    find = lambda frag: next(c for c in df.columns if frag in c)
    out = {"responses": len(df),
           "age_groups": df[find("age")].value_counts().to_dict(),
           "share_agree_motivated": share(find("stay motivated"), ["Agree", "Strongly agree"]),
           "share_agree_more_enjoyable": share(find("more enjoyable"), ["Agree", "Strongly agree"]),
           "share_agree_exercise_more": share(find("To exercise more"), ["Agree", "Strongly agree"]),
           "share_agree_change_diet": share(find("To change your diet"), ["Agree", "Strongly agree"]),
           "share_agree_improved_sleep": share(find("improved your sleep"), ["Agree", "Strongly agree"]),
           "tracking_frequency": df[find("track fitness data")].value_counts().to_dict(),
           "engagement": df[find("How engaged")].value_counts().to_dict()}
    (OUT / "survey_summary.json").write_text(json.dumps(out, indent=2, default=str))
    metrics["survey"] = {"responses": len(df)}


if __name__ == "__main__":
    train_calories(); train_risk(); train_sleep(); summarise_survey()
    (OUT / "model_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    print(json.dumps(metrics, indent=2, default=str))
