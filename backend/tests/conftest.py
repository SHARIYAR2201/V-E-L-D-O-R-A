import os, shutil, tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "veldora.db").exists():
    raise RuntimeError("Run `python -m scripts.ingest` first: tests use the ingested reference data.")
_tmp = Path(tempfile.mkdtemp()) / "test.db"
shutil.copy(ROOT / "veldora.db", _tmp)
os.environ["VELDORA_DATABASE_URL"] = f"sqlite:///{_tmp}"
os.environ["VELDORA_ADMIN_EMAILS"] = "boss@example.com"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def signup(client, email, pw="correct-horse-1"):
    r = client.post("/api/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def user(client):
    import uuid
    h = signup(client, f"{uuid.uuid4().hex[:8]}@example.com")
    r = client.put("/api/me/profile", headers=h, json={"age": 34, "sex": "male", "height_cm": 178, "weight_kg": 88, "activity_level": "moderate",
                                                     "goal_type": "lose", "target_weight_kg": 80, "equipment": ["dumbbells"]})
    assert r.status_code == 200, r.text
    return h
