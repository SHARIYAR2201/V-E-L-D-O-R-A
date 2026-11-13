"""Render the dataset section of README.md from data/datasets.yml.

    python -m scripts.sync_readme          # rewrite README and the backend mirror
    python -m scripts.sync_readme --check  # exit 1 if either copy is out of sync (used by tests/CI)

The backend mirror exists because the Vercel FastAPI service bundle only includes backend/.
"""
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "datasets.yml"
MIRROR = ROOT / "backend" / "data" / "datasets.yml"
START, END = "<!-- DATASETS:START -->", "<!-- DATASETS:END -->"


def render() -> str:
    reg = yaml.safe_load(REGISTRY.read_text())["datasets"]
    out = ["### Dataset register", "",
           "| Dataset | Version | Licence | Purpose | Status in this build | Verified |", "|---|---|---|---|---|---|"]
    for d in reg:
        cell = lambda k: " ".join(str(d[k]).split()).replace("|", "/")
        out.append(f"| **{cell('name')}**<br>{cell('source')} | {cell('version')} | {cell('license')} | {cell('purpose')} | {cell('status')} | {'yes' if d['verified'] else '**no - owner to complete**'} |")
    out += ["", "### References (APA 7)", ""]
    for d in sorted(reg, key=lambda x: " ".join(x["citation"].split()).lower()):
        out.append(f"- {' '.join(d['citation'].split())}")
    return "\n".join(out)


def main():
    readme = ROOT / "README.md"
    text = readme.read_text()
    a, b = text.index(START) + len(START), text.index(END)
    new = text[:a] + "\n" + render() + "\n" + text[b:]
    mirror_ok = MIRROR.exists() and MIRROR.read_text() == REGISTRY.read_text()
    if "--check" in sys.argv:
        sys.exit(0 if new == text and mirror_ok else 1)
    readme.write_text(new)
    MIRROR.parent.mkdir(exist_ok=True)
    MIRROR.write_text(REGISTRY.read_text())


if __name__ == "__main__":
    main()
