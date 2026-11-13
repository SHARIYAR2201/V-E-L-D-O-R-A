import json
from pathlib import Path
import yaml
from fastapi import APIRouter
from ..config import settings
from ..disclaimers import DISCLAIMERS

router = APIRouter(prefix="/meta", tags=["meta"])


def _datasets_file() -> Path:
    # Local checkouts keep the registry at <repo>/data/datasets.yml; the Vercel
    # service bundle only contains backend/, so it carries a mirror in backend/data.
    candidates = [Path(settings.data_dir) / "datasets.yml", Path(settings.artifacts_dir).parent / "data" / "datasets.yml"]
    return next((p for p in candidates if p.exists()), candidates[0])


@router.get("/datasets")
def datasets():
    d = yaml.safe_load(_datasets_file().read_text())["datasets"]
    return {"datasets": d, "unverified_count": sum(not x["verified"] for x in d), "disclaimers": DISCLAIMERS}


@router.get("/disclaimers")
def disclaimers():
    return {"disclaimers": DISCLAIMERS}
