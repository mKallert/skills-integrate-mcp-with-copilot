import urllib.parse

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Import here so we can set DB_PATH before init
    import src.app as app_mod

    # Use an isolated test database
    test_db = tmp_path / "test_activities.db"
    monkeypatch.setattr(app_mod, "DB_PATH", test_db)

    # Initialize database
    app_mod.init_db()

    client = TestClient(app_mod.app)
    return client


def test_get_activities(client):
    resp = client.get("/activities")
    assert resp.status_code == 200
    data = resp.json()
    assert "Chess Club" in data
    assert isinstance(data["Chess Club"]["participants"], list)


def test_signup_and_unregister(client):
    activity = "Chess Club"
    email = "tester@example.com"

    # Signup
    signup_url = f"/activities/{urllib.parse.quote(activity)}/signup?email={urllib.parse.quote(email)}"
    r = client.post(signup_url)
    assert r.status_code == 200
    assert "Signed up" in r.json().get("message", "")

    # Confirm participant present
    r = client.get("/activities")
    participants = r.json()[activity]["participants"]
    assert email in participants

    # Unregister
    unregister_url = f"/activities/{urllib.parse.quote(activity)}/unregister?email={urllib.parse.quote(email)}"
    r = client.delete(unregister_url)
    assert r.status_code == 200
    assert "Unregistered" in r.json().get("message", "")

    # Confirm removed
    r = client.get("/activities")
    participants = r.json()[activity]["participants"]
    assert email not in participants


def test_signup_duplicate_returns_400(client):
    activity = "Chess Club"
    email = "dup@example.com"

    signup_url = f"/activities/{urllib.parse.quote(activity)}/signup?email={urllib.parse.quote(email)}"
    r1 = client.post(signup_url)
    assert r1.status_code == 200
    r2 = client.post(signup_url)
    assert r2.status_code == 400
    assert "already" in r2.json().get("detail", "").lower()
