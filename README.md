# V-E-L-D-O-R-A

**Virtual Enhanced Lifestyle, Diet, Optimization, Recommendation & Analytics**

An informational health, nutrition, fitness and wellness platform: FastAPI + PostgreSQL + Redis backend, Next.js 14 + Tailwind + Framer Motion + Three.js + Recharts frontend.

> V-E-L-D-O-R-A provides informational health, nutrition, and fitness guidance only. This platform is not a medical device. This platform does not diagnose, treat, cure, or prevent disease. Predictions, calorie estimations, and recommendations are estimates and should not replace professional medical advice.

## 1. What is built (and what is not)

| Area | State |
|---|---|
| Auth: register, login, logout (token revocation), email verification, forgot/reset password, Google sign-in, protected routes | Built, tested. Email is a dev outbox (logs); wire SMTP/SES in `app/mailer.py`. Google needs `VELDORA_GOOGLE_CLIENT_ID` and is untested without credentials. |
| Profile, 17 health conditions + custom, allergies, diets, equipment | Built, tested |
| BMI / BMR (Mifflin-St Jeor) / TDEE, history | Built, tested |
| Food search, meal logging, macros, 4 meal slots | Built, tested (USDA data) |
| NLP food logging with confirmation | Built, tested (rule-based parser; no LLM) |
| AI diet planner (daily/weekly) with reasons and rule checks | Built, tested (rule-based selection) |
| Workout planner + progressive overload + condition safety caps | Built, tested |
| Calorie burn (MET x kg x h) | Built, tested |
| Sleep, hydration, weight tracking, achievements | Built, tested |
| Contextual assistant | Built (deterministic, grounded in your logs; no external LLM call) |
| ML: weight trend, goal ETA, consistency, adherence, behaviour patterns | Built (linear regression + rules, with confidence labels) |
| Admin: users, foods, dataset/model audit | Built (basic) |
| Data Sources & Attribution page (`/data-sources`) | Built, driven by `data/datasets.yml` |
| Landing, dashboard, coach, nutrition, workouts, progress, recovery, achievements, pricing, profile, admin pages | Built; `next build` passes. Not browser-tested or Lighthouse-audited. |
| Not built | Food image recognition (Food-101, UECFood256 are cited but unused), Random Forest/XGBoost on user data, payments, community posts/leaderboards, marketplace, OpenAI/Gemini calls, GSAP |

The dataset-trained models are **not deployed** because the audit showed they carry no usable signal (section 6).

## 2. Architecture

```
User data -> Analytics (insights.py) -> Rule engine (rules.py) -> ML layer (linear models) -> Recommendation (planner.py, assistant.py) -> UI
```

Rules (conditions, allergies, diets, safety floors) are applied as hard filters before and after any model output and always win.

```
backend/app/{routers,services,models.py,security.py}   FastAPI, SQLAlchemy 2
backend/scripts/{ingest,train,sync_readme}.py            data pipeline
data/raw/                                                supplied datasets
data/datasets.yml                                        attribution registry (source of truth)
frontend/src/{app,components,lib}                        Next.js app router
```

## 3. Database design

`users`, `profiles` (JSON: conditions, allergies, diets, equipment), `food_logs`, `workout_logs`, `sleep_logs`, `water_logs`, `weight_logs`, `achievements`, `auth_tokens` (hashed single-use). Reference tables from ingest: `foods` (per 100 g), `food_portions`, `nutrient_ref`, `met_activities`. SQLite by default; PostgreSQL via `VELDORA_DATABASE_URL`.

## 4. Methodology

**Nutrition values.** Never invented: every kcal/macro traces to a `foods` row from USDA data. The only non-dataset numbers are standard piece weights (e.g. egg 50 g) used when a count has no USDA portion; they are flagged "assumed" and need confirmation.

**NLP.** `text -> split items -> quantity/unit -> fuzzy match (rapidfuzz) -> USDA portion or explicit grams -> estimate -> user confirms -> log`. Items with no match or unknown amount are returned with an issue, never guessed.

**Diet planner.** Condition rules -> excluded keywords/flags -> candidate foods per role -> portions scaled to calorie share -> post-check against limits (carb share, sodium, saturated fat). Unmet checks are reported in `rule_checks` and `warnings`. Limitations: ingredients not recipes; no budget (no price data); with diabetes + vegetarian the carbohydrate cap is currently **not met** and the plan says so.

**Targets.** Mifflin-St Jeor x activity factor; deficit capped at ~1% body weight/week, calorie floors 1,500/1,200 kcal; under-18 and kidney-disease profiles receive no automatic plan; "underweight" overrides a weight-loss goal.

**Weight prediction.** Ordinary least squares on the user's own weigh-ins, with a widening range and confidence (low/medium/high from sample size and R²). It is a trend extrapolation, never a promise.

**Calories burned.** kcal = MET x kg x hours. MET values: a 23-activity seed from the 2011 Compendium; replace with the full official file via `python -m scripts.ingest --met-file`.

## 5. Install and run

```bash
cd backend && pip install -r requirements.txt
python -m scripts.ingest && python -m scripts.train
python -m pytest -q
uvicorn app.main:app --reload                 # http://localhost:8000/docs
cd ../frontend && npm install && npm run dev  # http://localhost:3000
```

Docker: `cp .env.example .env`, edit secrets, `docker compose up --build`.

**Environment variables** (prefix `VELDORA_`): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` (must change), `GOOGLE_CLIENT_ID`, `CORS_ORIGINS`, `ADMIN_EMAILS`, `DATA_DIR`; frontend `API_URL`.

**Deployment.** Put a TLS terminator in front, set a strong `JWT_SECRET`, use managed Postgres/Redis, run `ingest` once per release. CI is in `.github/workflows/ci.yml`.

## 6. Dataset audit results

Produced by `scripts/ingest.py` and `scripts/train.py` (see `backend/artifacts/`).

- **USDA load:** 469 Foundation Foods rows, 91 lack energy and were dropped, 329 distinct foods kept; +1,680 FNDDS ingredient rows from the Supporting Data; 142 portions. The JSON release was cross-checked: 321 foods matched by description, max energy difference 5.98 kcal.
- **exercise_dataset.csv (3,864 rows):** exercise names are anonymised ("Exercise 1-10") and no feature correlates with calories burned (|r| <= 0.04). Holdout R2: linear -0.005, random forest -0.036, XGBoost -0.088. **Not used**; MET is used instead.
- **diabetes_risk_prediction_dataset.csv (50,000 rows):** 20,810 missing cells; classes High 36,593 / Moderate 12,937 / Low 470; label tracks an excluded score column. Lifestyle-only models reach 0.745 accuracy against a 0.732 majority baseline and never recover "Low". **Not used**; no risk score is shown. Labels look synthetic.
- **Sleep_health_and_lifestyle_dataset.csv (374 rows):** holdout R2 0.908 for a linear model of sleep quality, which reflects a clean synthetic structure. Used only for descriptive benchmarks (duration percentiles, quality by age band).
- **survey_605.csv (30 responses):** aggregates only (80% agree wearables keep them motivated; 87% exercise more). Informs reminder/streak design; too small for inference and includes minors.

## 7. API

Interactive docs at `/docs`. Main groups under `/api`: `auth/*`, `me`, `me/profile`, `me/metrics`, `me/dashboard`, `conditions`, `foods/search`, `foods/barcode/{code}` (Open Food Facts), `nutrition/parse|log|day`, `plans/diet`, `plans/workout`, `activities`, `workouts`, `sleep`, `water`, `weight`, `achievements`, `ai/assistant`, `ai/insights`, `meta/datasets`, `admin/*` (admin role).

## 8. Datasets, credits and references

All datasets supplied for this project are listed below. The table and reference list are generated from `data/datasets.yml` by `python -m scripts.sync_readme`; tests fail if a dataset is missing here or the README is stale. Entries marked **no** could not be verified from the supplied files and need the publisher, URL and licence filled in before you publish.

<!-- DATASETS:START -->
### Dataset register

| Dataset | Version | Licence | Purpose | Status in this build | Verified |
|---|---|---|---|---|---|
| **USDA FoodData Central - Foundation Foods (CSV)**<br>https://fdc.nal.usda.gov/download-datasets | April 2026 release (FoodData_Central_foundation_food_csv_2026-04-30.zip) | CC0 1.0 Universal (public domain dedication) | Primary nutrition database (per-100 g energy and nutrients, household portions, food categories) | loaded (329 distinct foods with energy values; 142 portions) by scripts/ingest.py | yes |
| **USDA FoodData Central - Foundation Foods (JSON)**<br>https://fdc.nal.usda.gov/download-datasets | April 2026 release (FoodData_Central_foundation_food_json_2026-04-30.zip) | CC0 1.0 Universal (public domain dedication) | Integrity cross-check of the CSV ingest (food count and energy agreement) | read by scripts/ingest.py for validation only; not a second source of values | yes |
| **USDA FoodData Central - Supporting Data for Download (CSV)**<br>https://fdc.nal.usda.gov/download-datasets | October 2022 release (FoodData_Central_Supporting_Data_csv_2022-10-28.zip) | CC0 1.0 Universal (public domain dedication) | Nutrient reference table (474 nutrients) and FNDDS ingredient nutrient values (1,680 additional ingredients incl. cooked staples) | loaded by scripts/ingest.py; ingredient rows are stored with source "USDA FNDDS ingredient values (Supporting Data 2022-10-28)" | yes |
| **FoodData Central (system description paper, cite alongside the data)**<br>https://doi.org/10.1093/ajcn/nqab397 | 2022 | n/a (journal article) | Recommended scholarly reference for FoodData Central | reference only | yes |
| **Compendium of Physical Activities**<br>https://pacompendium.com/ | 2011 values (seed table of 23 activities); 2024 update is the current edition | Free to use with citation; confirm terms at pacompendium.com | MET values for calorie-burn estimation (kcal = MET x weight_kg x hours) | 23 common activities transcribed into backend/app/services/mets.py as a seed; NOT the full file. Load the official file with `python -m scripts.ingest --met-file` | yes |
| **2024 Adult Compendium of Physical Activities**<br>https://pacompendium.com/ | 2024 | Free to use with citation; confirm terms at pacompendium.com | Current edition to use when loading the full MET file | reference only (not bundled) | yes |
| **Open Food Facts**<br>https://world.openfoodfacts.org/ | live API (no snapshot bundled) | Open Database License (ODbL) 1.0 for the database; Database Contents License for contents; CC BY-SA for images | Packaged-food and barcode lookup | GET /api/foods/barcode/{code} queries the public API at request time; nothing is stored; contributors must be credited and derived databases share-alike | yes |
| **Food-101**<br>https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/ | 2014 (101,000 images, 101 classes) | Research use; images originate from foodspotting.com - see the dataset page before any commercial use | Planned food-image recognition (photo logging) | not loaded; image recognition is not implemented in this release | yes |
| **UEC FOOD 256 (UECFood256)**<br>https://foodcam.mobi/dataset256.html | 256 food categories | Research use; confirm terms on the dataset page | Planned food-image recognition (photo logging) | not loaded; image recognition is not implemented in this release | **no - owner to complete** |
| **exercise_dataset.csv (3,864 rows; calories burned vs duration, heart rate, weight, intensity)**<br>Unknown - not stated in the file. [OWNER TO COMPLETE: publisher/URL] | as supplied by the project owner | Unknown. [OWNER TO COMPLETE] | Evaluated as a data-driven calorie-burn model | trained and audited by scripts/train.py; NOT deployed (no learnable signal, holdout R2 <= 0) | **no - owner to complete** |
| **diabetes_risk_prediction_dataset.csv (50,000 rows)**<br>Unknown - not stated in the file. [OWNER TO COMPLETE: publisher/URL] | as supplied by the project owner | Unknown. [OWNER TO COMPLETE] | Evaluated as a lifestyle risk-indicator model | trained and audited by scripts/train.py; NOT deployed (barely beats the majority-class baseline; labels appear synthetic). No risk score is shown to users | **no - owner to complete** |
| **Sleep Health and Lifestyle Dataset (374 rows)**<br>Not stated in the file. Commonly distributed on Kaggle under this title. [OWNER TO COMPLETE: author, URL] | Sleep_health_and_lifestyle_dataset.csv, as supplied by the project owner | Unknown. [OWNER TO COMPLETE] | Descriptive sleep benchmarks (duration percentiles, quality by age band) and a linear model of sleep quality used for plain-language insights | loaded by scripts/train.py into artifacts/sleep_benchmarks.json and sleep_model.joblib; the data looks synthetic, so outputs are descriptive only | **no - owner to complete** |
| **survey_605.csv (fitness wearable survey, 30 responses, March 2023)**<br>Unknown (Google Forms export). [OWNER TO COMPLETE] | as supplied by the project owner | Unknown. [OWNER TO COMPLETE] | Product research on wearable engagement (informs reminders, streaks and tracking cadence); shown in the admin analytics view | summarised by scripts/train.py into artifacts/survey_summary.json; aggregate counts only, n=30, includes under-18 respondents so no row-level use | **no - owner to complete** |

### References (APA 7)

- [Author unknown]. (2023). Fitness wearable usage survey (survey_605.csv) [Data set]. Supplied by the V-E-L-D-O-R-A project owner.
- [Author unknown]. (n.d.). Sleep health and lifestyle dataset [Data set]. Supplied by the V-E-L-D-O-R-A project owner.
- [Author/publisher unknown]. (n.d.). diabetes_risk_prediction_dataset.csv [Data set]. Supplied by the V-E-L-D-O-R-A project owner.
- [Author/publisher unknown]. (n.d.). exercise_dataset.csv [Data set]. Supplied by the V-E-L-D-O-R-A project owner.
- Ainsworth, B. E., Haskell, W. L., Herrmann, S. D., Meckes, N., Bassett, D. R., Jr., Tudor-Locke, C., Greer, J. L., Vezina, J., Whitt-Glover, M. C., & Leon, A. S. (2011). 2011 Compendium of Physical Activities: A second update of codes and MET values. Medicine & Science in Sports & Exercise, 43(8), 1575-1581. https://doi.org/10.1249/MSS.0b013e31821ece12
- Bossard, L., Guillaumin, M., & Van Gool, L. (2014). Food-101 - Mining discriminative components with random forests. In D. Fleet, T. Pajdla, B. Schiele, & T. Tuytelaars (Eds.), Computer Vision - ECCV 2014 (Lecture Notes in Computer Science, Vol. 8694, pp. 446-461). Springer. https://doi.org/10.1007/978-3-319-10599-4_29
- Fukagawa, N. K., McKillop, K., Pehrsson, P. R., Moshfegh, A., Harnly, J., & Finley, J. (2022). USDA's FoodData Central: What is it and why is it needed today? The American Journal of Clinical Nutrition, 115(3), 619-624. https://doi.org/10.1093/ajcn/nqab397
- Herrmann, S. D., Willis, E. A., Ainsworth, B. E., Barreira, T. V., Hastert, M., Kracht, C. L., Schuna, J. M., Jr., Cai, Z., Quan, M., Tudor-Locke, C., Whitt-Glover, M. C., & Jacobs, D. R., Jr. (2024). 2024 Adult Compendium of Physical Activities: A third update of the energy costs of human activities. Journal of Sport and Health Science, 13(1), 6-12. https://doi.org/10.1016/j.jshs.2023.10.010
- Kawano, Y., & Yanai, K. (2014). FoodCam-256: A large-scale real-time mobile food recognition system employing high-dimensional features and compression of classifier weights. Proceedings of the 22nd ACM International Conference on Multimedia. https://foodcam.mobi/dataset256.html
- Open Food Facts contributors. (n.d.). Open Food Facts: The free food products database [Data set]. https://world.openfoodfacts.org/
- U.S. Department of Agriculture, Agricultural Research Service. (2022). FoodData Central: Supporting data for download (October 2022 release) [Data set]. U.S. Department of Agriculture. https://fdc.nal.usda.gov/
- U.S. Department of Agriculture, Agricultural Research Service. (2026). FoodData Central: Foundation Foods (April 2026 release) [Data set]. U.S. Department of Agriculture. https://fdc.nal.usda.gov/
- U.S. Department of Agriculture, Agricultural Research Service. (2026). FoodData Central: Foundation Foods (April 2026 release, JSON) [Data set]. U.S. Department of Agriculture. https://fdc.nal.usda.gov/
<!-- DATASETS:END -->

## 9. Licence

Application code: choose a licence for your project (none is set). Data keeps the licences above; Open Food Facts use requires attribution and share-alike for derived databases.

## 10. Ethical AI statement

The platform gives informational guidance only. It never diagnoses or prescribes; health-condition inputs only add safety constraints; rules override models; predictions carry ranges and confidence and are never presented as certain; every recommendation can explain why; nutrition values come only from approved datasets; users confirm food estimates before logging; models that failed validation are withheld rather than shipped; synthetic or unverified datasets are labelled as such.
