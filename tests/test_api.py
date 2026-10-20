"""
Integration and API route tests using FastAPI TestClient.
Tests session flow with dynamic CAPTCHAs, direct CNR search, and error responses.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_mock_mode_for_tests(monkeypatch):
    """Ensure test suite runs reliably regardless of live eCourts uptime."""
    monkeypatch.setattr(settings, "ENABLE_MOCK_FALLBACK", True)


def test_root_and_health():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert "active_sessions" in health_data


def test_captcha_session_workflow_dynamic():
    # 1. Create a session
    resp1 = client.post("/api/v1/search/session")
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert "captcha" in data1
    captcha1 = data1["captcha"]
    assert len(captcha1) == 5

    # 2. Create another session and verify the CAPTCHA is different / dynamic!
    resp2 = client.post("/api/v1/search/session")
    assert resp2.status_code == 201
    data2 = resp2.json()
    captcha2 = data2["captcha"]
    assert len(captcha2) == 5

    # Check status
    session_id = data1["session_id"]
    status_resp = client.get(f"/api/v1/search/session/{session_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["captcha"] == captcha1


def test_cnr_search_success_with_dynamic_captcha():
    # 1. Initiate session to get dynamic CAPTCHA
    sess_resp = client.post("/api/v1/search/session")
    assert sess_resp.status_code == 201
    sess_data = sess_resp.json()
    session_id = sess_data["session_id"]
    dynamic_captcha = sess_data["captcha"]

    # 2. Submit search with the exact dynamic CAPTCHA returned
    payload = {
        "session_id": session_id,
        "captcha": dynamic_captcha,
        "cnr": "MHAU019999992015",
    }
    resp = client.post("/api/v1/cases/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["search_type"] == "cnr"
    assert data["total_results"] == 1

    case = data["results"][0]
    assert case["cnr"] == "MHAU019999992015"
    assert case["case_type"] == "Special Civil Suit (SCS)"
    assert case["status"] == "DISPOSED"
    assert len(case["case_history"]) > 0
    assert len(case["orders"]) > 0


def test_cnr_search_direct_without_session():
    # Submit search directly with just CNR (auto-creates session and solves captcha)
    payload = {
        "cnr": "MHAU019999992015",
    }
    resp = client.post("/api/v1/cases/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["results"]) == 1


def test_cnr_search_invalid_cnr():
    payload = {
        "cnr": "INVALIDCNR123",
    }
    resp = client.post("/api/v1/cases/search", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"


def test_cnr_search_invalid_captcha():
    sess_resp = client.post("/api/v1/search/session")
    assert sess_resp.status_code == 201
    sess_data = sess_resp.json()
    session_id = sess_data["session_id"]
    dynamic_captcha = sess_data["captcha"]

    # Intentionally enter wrong captcha
    wrong_captcha = "wrong" if dynamic_captcha != "wrong" else "error"
    payload = {
        "session_id": session_id,
        "captcha": wrong_captcha,
        "cnr": "MHAU019999992015",
    }
    resp = client.post("/api/v1/cases/search", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "CAPTCHA_INVALID"


def test_unified_get_search_direct():
    # Direct GET query with just CNR - no captcha or session required!
    resp = client.get("/api/v1/cases/search?cnr=MHAU019999992015")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["results"]) == 1


def test_unified_get_search_with_session():
    sess_resp = client.post("/api/v1/search/session")
    assert sess_resp.status_code == 201
    sess_data = sess_resp.json()
    session_id = sess_data["session_id"]
    dynamic_captcha = sess_data["captcha"]

    resp = client.get(
        f"/api/v1/cases/search?cnr=MHAU019999992015&session_id={session_id}&captcha={dynamic_captcha}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["results"]) == 1


def test_expired_session():
    payload = {
        "session_id": "ec_non_existent_or_expired",
        "captcha": "abc12",
        "cnr": "MHAU019999992015",
    }
    resp = client.post("/api/v1/cases/search", json=payload)
    assert resp.status_code == 410
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SESSION_EXPIRED"


def test_search_by_case_number():
    payload = {
        "state_code": "MH",
        "district_code": "AU",
        "court_complex_code": "01",
        "case_type": "Civil Suit",
        "case_number": "189",
        "case_year": 2015,
    }
    resp = client.post("/api/v1/cases/search/case-number", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["search_type"] == "case_number"
    assert len(data["results"]) == 1


def test_search_by_party_name():
    payload = {
        "state_code": "MH",
        "district_code": "AU",
        "court_complex_code": "01",
        "party_name": "Rameshwar Patil",
    }
    resp = client.post("/api/v1/cases/search/party", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["search_type"] == "party_name"
    assert data["results"][0]["petitioner"] == "Rameshwar Patil"


def test_search_orders():
    payload = {
        "state_code": "MH",
        "district_code": "AU",
        "court_complex_code": "01",
        "order_date": "14-04-2015",
    }
    resp = client.post("/api/v1/orders/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["search_type"] == "court_orders"
    assert len(data["results"]) > 0
    assert data["results"][0]["order_date"] == "14-04-2015"
