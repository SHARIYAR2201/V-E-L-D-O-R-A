import subprocess, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_readme_cites_every_dataset_in_registry():
    text = (ROOT / "README.md").read_text()
    for d in yaml.safe_load((ROOT / "data" / "datasets.yml").read_text())["datasets"]:
        assert " ".join(d["citation"].split()) in text, f"{d['id']} citation missing from README"


def test_readme_in_sync_with_registry():
    r = subprocess.run([sys.executable, "-m", "scripts.sync_readme", "--check"], cwd=ROOT / "backend")
    assert r.returncode == 0, "README dataset section is stale: run `python -m scripts.sync_readme`"


def test_every_supplied_file_is_registered():
    reg = yaml.safe_load((ROOT / "data" / "datasets.yml").read_text())["datasets"]
    blob = " ".join(f"{d['name']} {d['version']}" for d in reg)
    for f in sorted(p.name for p in (ROOT / "data" / "raw").rglob("*") if p.is_file()):
        assert f in blob, f"{f} is in data/raw but not in datasets.yml"
