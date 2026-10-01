import json
from pathlib import Path
import yaml
from fastapi import APIRouter
from ..config import settings
from ..disclaimers import DISCLAIMERS

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/datasets")
def datasets():
    d = yaml.safe_load((Path(settings.data_dir) / "datasets.yml").read_text())["datasets"]
    return {"datasets": d, "unverified_count": sum(not x["verified"] for x in d), "disclaimers": DISCLAIMERS}


@router.get("/disclaimers")
def disclaimers():
    return {"disclaimers": DISCLAIMERS}
