"""Load the supplied datasets into the database.

    python -m scripts.ingest [--met-file path.csv]

USDA FoodData Central (Foundation Foods CSV, 2026-04-30)  -> foods, food_portions
USDA FoodData Central (Supporting Data CSV, 2022-10-28)   -> nutrient_ref
USDA FoodData Central (Foundation Foods JSON, 2026-04-30) -> cross-check only (row-count / energy agreement)
Compendium seed table (or --met-file)                      -> met_activities
Kaggle CSVs are consumed by scripts/train.py, not loaded into SQL.
"""
import argparse, io, json, zipfile
from pathlib import Path
import pandas as pd
from sqlalchemy import delete
from app.config import settings
from app.db import Base, engine, SessionLocal
from app import models as m
from app.services.mets import SEED

USDA = Path(settings.data_dir) / "raw" / "usda"
NUT = {1008: "kcal", 2047: "kcal_gen", 2048: "kcal_spec", 1003: "protein_g", 1004: "fat_g", 1005: "carb_g",
       1050: "carb_sum", 1079: "fiber_g", 2000: "sugar_g", 1093: "sodium_mg", 1258: "sat_fat_g", 1253: "cholesterol_mg"}


def read_zip(pattern: str, member_suffix: str, **kw) -> pd.DataFrame:
    z = zipfile.ZipFile(next(USDA.glob(pattern)))
    want = member_suffix.lstrip('/')
    name = next(n for n in z.namelist() if n.split('/')[-1] == want)
    return pd.read_csv(io.BytesIO(z.read(name)), low_memory=False, **kw)


def foundation_foods():
    pat = "FoodData_Central_foundation_food_csv_*.zip"
    food = read_zip(pat, "/food.csv")
    food = food[food.data_type == "foundation_food"]
    cat = read_zip(pat, "/food_category.csv").set_index("id").description
    fn = read_zip(pat, "/food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn.fdc_id.isin(food.fdc_id) & fn.nutrient_id.isin(NUT)]
    wide = fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="mean").rename(columns=NUT)
    for c in NUT.values():
        if c not in wide:
            wide[c] = pd.NA
    # Energy: use the reported kcal value, else an Atwater energy value that USDA itself reports. Never computed here.
    wide["kcal"] = wide["kcal"].fillna(wide["kcal_gen"]).fillna(wide["kcal_spec"])
    wide["carb_g"] = wide["carb_g"].fillna(wide["carb_sum"])
    df = food.set_index("fdc_id").join(wide)
    df["category"] = df.food_category_id.map(cat)
    total = len(df)
    df = df.dropna(subset=["kcal"])
    dropped = total - len(df)
    # The release lists some foods several times (e.g. different sample years): collapse on description.
    df = df.reset_index().sort_values("fdc_id")
    canon = df.groupby("description").fdc_id.min()
    id_map = df.set_index("fdc_id").description.map(canon)
    cols = ["kcal", "protein_g", "fat_g", "carb_g", "fiber_g", "sugar_g", "sodium_mg", "sat_fat_g", "cholesterol_mg"]
    agg = df.groupby("description").agg({**{c: "mean" for c in cols}, "category": "first", "fdc_id": "min"}).reset_index()
    portions = read_zip(pat, "/food_portion.csv")
    units = read_zip(pat, "/measure_unit.csv").set_index("id").name
    portions = portions[portions.fdc_id.isin(id_map.index)].copy()
    portions["fdc_id"] = portions.fdc_id.map(id_map)
    label = portions.portion_description.fillna("").astype(str)
    label = label.where(label.str.strip() != "", portions.modifier.fillna("").astype(str))
    label = label.where(label.str.strip() != "", portions.measure_unit_id.map(units).fillna("unit").astype(str))
    portions["unit_label"] = label
    portions = portions.dropna(subset=["gram_weight", "amount"]).drop_duplicates(["fdc_id", "unit_label", "amount", "gram_weight"])
    return agg, portions, dropped, total


FNDDS_NBR = {208: "kcal", 203: "protein_g", 204: "fat_g", 205: "carb_g", 291: "fiber_g", 269: "sugar_g",
             307: "sodium_mg", 606: "sat_fat_g", 601: "cholesterol_mg"}
FNDDS_SOURCE = "USDA FNDDS ingredient values (Supporting Data 2022-10-28)"


def fndds_ingredients(existing_desc: set, existing_ids: set) -> pd.DataFrame:
    """Second tier: ~1,900 ingredient rows (per 100 g) incl. cooked staples that Foundation Foods lacks."""
    d = read_zip("FoodData_Central_Supporting_Data_csv_*.zip", "fndds_ingredient_nutrient_value.csv")
    d = d.rename(columns={"ingredient code": "code", "Ingredient description": "description", "Nutrient code": "nbr",
                          "Nutrient value": "val", "FDC ID": "fdc_id"})
    d = d[d.nbr.isin(FNDDS_NBR)]
    wide = d.pivot_table(index=["code", "description"], columns="nbr", values="val", aggfunc="mean").rename(columns=FNDDS_NBR).reset_index()
    ids = d.groupby("code").fdc_id.min()
    wide["fdc_id"] = wide.code.map(ids)
    wide = wide.dropna(subset=["kcal", "fdc_id"])
    wide = wide[~wide.description.str.startswith("Babyfood")]
    wide = wide[~wide.description.isin(existing_desc) & ~wide.fdc_id.astype(int).isin(existing_ids)]
    wide = wide.drop_duplicates("description").drop_duplicates("fdc_id")
    wide["fdc_id"] = wide.fdc_id.astype(int)
    wide["category"] = None
    wide["source"] = FNDDS_SOURCE
    return wide.drop(columns=["code"])


def json_crosscheck(agg: pd.DataFrame) -> dict:
    z = zipfile.ZipFile(next(USDA.glob("FoodData_Central_foundation_food_json_*.zip")))
    data = [f for f in json.loads(z.read(z.namelist()[0]))["FoundationFoods"] if f]
    jd = {}
    for f in data:
        for n in f.get("foodNutrients", []):
            if n["nutrient"]["id"] in (1008, 2047, 2048):
                jd.setdefault(f["description"], n["amount"])
                break
    both = agg[agg.description.isin(jd)]
    diffs = [abs(r.kcal - jd[r.description]) for r in both.itertuples()]
    return {"json_foods": len(data), "json_with_energy": len(jd), "matched_by_description": len(both),
            "max_abs_kcal_diff": round(max(diffs), 2) if diffs else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--met-file")
    args = ap.parse_args()
    Base.metadata.create_all(engine)
    agg, portions, dropped, total = foundation_foods()
    nutrients = read_zip("FoodData_Central_Supporting_Data_csv_*.zip", "nutrient.csv")
    check = json_crosscheck(agg)
    n_foundation = len(agg)
    extra = fndds_ingredients(set(agg.description), set(agg.fdc_id.astype(int)))
    agg["source"] = "USDA FDC Foundation Foods 2026-04-30"
    agg = pd.concat([agg, extra[agg.columns.intersection(extra.columns)]], ignore_index=True)
    with SessionLocal() as db:
        for t in (m.FoodPortion, m.Food, m.NutrientRef, m.MetActivity):
            db.execute(delete(t))
        db.bulk_insert_mappings(m.Food, [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in agg.to_dict("records")])
        db.bulk_insert_mappings(m.FoodPortion, [dict(fdc_id=int(r.fdc_id), amount=float(r.amount), unit_label=r.unit_label[:200],
                                                     gram_weight=float(r.gram_weight)) for r in portions.itertuples()])
        db.bulk_insert_mappings(m.NutrientRef, [dict(id=int(r['id']), name=r['name'], unit_name=r['unit_name']) for r in nutrients.to_dict('records')])
        if args.met_file:
            mets = pd.read_csv(args.met_file)
            rows = [dict(key=r['key'], category=r['category'], name=r['name'], met=float(r['met']), compendium_code=str(r['code']),
                         source=Path(args.met_file).name) for r in mets.to_dict('records')]
            src = args.met_file
        else:
            rows = [dict(key=k, category=c, name=n, met=v, source="Compendium 2011 (seed, verify)") for k, c, n, v in SEED]
            src = "seed"
        db.bulk_insert_mappings(m.MetActivity, rows)
        db.commit()
    report = {"foundation_foods_in_csv": total, "dropped_without_energy": dropped, "foods_loaded": len(agg), "foods_foundation": n_foundation, "foods_fndds_ingredients": len(extra),
              "portions_loaded": len(portions), "nutrient_ref_rows": len(nutrients), "met_rows": len(rows), "met_source": src,
              "json_crosscheck": check}
    out = Path(settings.artifacts_dir); out.mkdir(exist_ok=True)
    (out / "ingest_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
