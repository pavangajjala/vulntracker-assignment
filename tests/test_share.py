"""Tests for the Shared Report Link feature (Task 1)."""
from datetime import timedelta

from tests.test_api import TestingSessionLocal, auth_headers, client, register_and_login

import models


def make_scan(token, title="Exposed admin panel"):
    resp = client.post("/scans", json={
        "title": title,
        "severity": "high",
        "affected_component": "admin UI",
    }, headers=auth_headers(token))
    return resp.json()["id"]


def share(token, scan_id, body=None):
    return client.post(f"/scans/{scan_id}/share", json=body, headers=auth_headers(token))


def token_from(url):
    return url.rsplit("/", 1)[-1]


def test_share_link_without_password():
    token = register_and_login()
    scan_id = make_scan(token)
    resp = share(token, scan_id)
    assert resp.status_code == 201
    url = resp.json()["share_url"]
    assert url.startswith("http://localhost:8000/share/")

    view = client.get(f"/share/{token_from(url)}")
    assert view.status_code == 200
    assert view.json()["title"] == "Exposed admin panel"
    assert "owner_id" not in view.json()


def test_share_link_with_password():
    token = register_and_login()
    scan_id = make_scan(token)
    url = share(token, scan_id, {"password": "correct-horse"}).json()["share_url"]
    t = token_from(url)

    assert client.get(f"/share/{t}").status_code == 401
    assert client.get(f"/share/{t}?password=wrong-password").status_code == 401
    assert client.get(f"/share/{t}?password=correct-horse").status_code == 200
    assert client.get(f"/share/{t}", headers={"X-Share-Password": "correct-horse"}).status_code == 200


def test_share_link_locks_after_too_many_wrong_passwords():
    token = register_and_login()
    scan_id = make_scan(token)
    t = token_from(share(token, scan_id, {"password": "correct-horse"}).json()["share_url"])
    for _ in range(5):
        client.get(f"/share/{t}?password=guess-guess")
    # Even the right password no longer works once the link is locked.
    assert client.get(f"/share/{t}?password=correct-horse").status_code == 404


def test_share_link_expires_after_24_hours():
    token = register_and_login()
    scan_id = make_scan(token)
    t = token_from(share(token, scan_id).json()["share_url"])

    db = TestingSessionLocal()
    link = db.query(models.ShareLink).first()
    link.expires_at = link.expires_at - timedelta(hours=24, seconds=1)
    db.commit()
    db.close()

    assert client.get(f"/share/{t}").status_code == 404


def test_cannot_share_someone_elses_scan():
    alice = register_and_login()
    scan_id = make_scan(alice)
    bob = register_and_login("bob", "bob@example.com", "password123")
    assert share(bob, scan_id).status_code == 404


def test_share_requires_login():
    assert client.post("/scans/1/share").status_code in (401, 403)


def test_unknown_token_is_404():
    assert client.get("/share/not-a-real-token").status_code == 404


def test_token_is_not_stored_in_plain_text():
    token = register_and_login()
    scan_id = make_scan(token)
    t = token_from(share(token, scan_id, {"password": "correct-horse"}).json()["share_url"])
    db = TestingSessionLocal()
    link = db.query(models.ShareLink).first()
    db.close()
    assert link.token_hash != t
    assert "correct-horse" not in (link.password_hash or "")


def test_share_password_too_short_is_rejected():
    token = register_and_login()
    scan_id = make_scan(token)
    assert share(token, scan_id, {"password": "short"}).status_code == 422