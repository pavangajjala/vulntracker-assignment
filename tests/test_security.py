"""Regression tests for the security fixes (Task 3).
Each of these fails on the original starter code and passes after the fix."""
import base64
import json
import logging

from tests.test_api import auth_headers, client, register_and_login


def make_scan(token, title):
    resp = client.post("/scans", json={
        "title": title,
        "severity": "high",
        "affected_component": "admin UI",
    }, headers=auth_headers(token))
    return resp.json()["id"]


def test_search_is_not_sql_injectable_and_only_returns_own_scans():
    alice = register_and_login()
    make_scan(alice, "Alice secret finding")
    bob = register_and_login("bob", "bob@example.com", "password123")
    make_scan(bob, "Bob finding")

    resp = client.get("/scans/search", params={"q": "' OR '1'='1"}, headers=auth_headers(bob))
    assert resp.status_code == 200
    assert resp.json()["count"] == 0

    resp = client.get("/scans/search", params={"q": "finding"}, headers=auth_headers(bob))
    titles = [r["title"] for r in resp.json()["results"]]
    assert titles == ["Bob finding"]


def test_cannot_read_another_users_scan():
    alice = register_and_login()
    scan_id = make_scan(alice, "Alice secret finding")
    bob = register_and_login("bob", "bob@example.com", "password123")
    assert client.get(f"/scans/{scan_id}", headers=auth_headers(bob)).status_code == 404


def test_unsigned_jwt_is_rejected():
    register_and_login()

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    forged = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': 'alice', 'exp': 9999999999})}."
    assert client.get("/scans", headers=auth_headers(forged)).status_code == 401


def test_passwords_are_not_logged(caplog):
    caplog.set_level(logging.INFO)
    client.post("/auth/register", json={"username": "carol", "email": "c@example.com", "password": "Sup3rS3cret!"})
    client.post("/auth/login", json={"username": "carol", "password": "Sup3rS3cret!"})
    client.post("/auth/login", json={"username": "carol", "password": "Wr0ngGuess!"})
    assert "Sup3rS3cret!" not in caplog.text
    assert "Wr0ngGuess!" not in caplog.text