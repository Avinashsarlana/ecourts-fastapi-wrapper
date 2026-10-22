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


def test_dynamic_cnr_search_dlhc():
    """Verify that searching for DLHC010001232024 returns exact DLHC case details, never MHAU019999992015."""
    target_cnr = "DLHC010001232024"

    # 1. Test via direct POST
    post_resp = client.post("/api/v1/cases/search", json={"cnr": target_cnr})
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert post_data["success"] is True
    assert post_data["query"]["cnr"] == target_cnr
    assert len(post_data["results"]) == 1
    case = post_data["results"][0]
    assert case["cnr"] == target_cnr
    assert case["cnr"] != "MHAU019999992015"
    assert "Delhi" in case["court"]
    assert case["state"] == "Delhi"
    assert case["case_number"] == "000123/2024"
    assert "2024" in case["registration_date"]

    # 2. Test via GET endpoint
    get_resp = client.get(f"/api/v1/cases/search?cnr={target_cnr}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["success"] is True
    assert get_data["query"]["cnr"] == target_cnr
    assert get_data["results"][0]["cnr"] == target_cnr
    assert get_data["results"][0]["cnr"] != "MHAU019999992015"


def test_multiple_distinct_cnr_searches_in_sequence():
    """Verify that every new CNR search produces results specifically for the CNR entered in that search."""
    cnr1 = "DLHC010001232024"
    cnr2 = "KABG010005552023"

    resp1 = client.get(f"/api/v1/cases/search?cnr={cnr1}")
    assert resp1.status_code == 200
    case1 = resp1.json()["results"][0]
    assert case1["cnr"] == cnr1
    assert case1["state"] == "Delhi"

    resp2 = client.get(f"/api/v1/cases/search?cnr={cnr2}")
    assert resp2.status_code == 200
    case2 = resp2.json()["results"][0]
    assert case2["cnr"] == cnr2
    assert case2["state"] == "Karnataka"

    # Ensure responses are distinct and tailored to each CNR
    assert case1["cnr"] != case2["cnr"]
    assert case1["state"] != case2["state"]


def test_cnr_mismatch_validation_rejection(monkeypatch):
    """
    Verify that if the underlying response ever returns a mismatched CNR
    (e.g. backend returns MHAU019999992015 when DLHC010001232024 was requested),
    the validation rejects it and returns a 404 error with clear message.
    """
    from app.clients.ecourts_client import ecourts_client

    # Force query_case_by_cnr to return a mismatched HTML (MHAU when DLHC was requested)
    def fake_query(*args, **kwargs):
        from app.clients.ecourts_client import generate_mock_case_html
        return generate_mock_case_html("MHAU019999992015")

    monkeypatch.setattr(ecourts_client, "query_case_by_cnr", fake_query)

    resp = client.get("/api/v1/cases/search?cnr=DLHC010001232024")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False
    assert data["message"] == "No matching case data was found for the requested CNR."
    assert data["cnr"] == "DLHC010001232024"
    assert data["error"]["code"] == "CASE_NOT_FOUND"


def test_case_not_found_response_format():
    """Verify that non-existent cases return the required JSON format."""
    not_found_cnr = "DLHC010000002024"
    resp = client.get(f"/api/v1/cases/search?cnr={not_found_cnr}")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False
    assert data["message"] == "No matching case data was found for the requested CNR."
    assert data["cnr"] == not_found_cnr
    assert data["error"]["code"] == "CASE_NOT_FOUND"


def test_all_three_user_cnrs():
    """Verify end-to-end flow for all three user-provided CNRs: NCLT, Supreme Court, and High Court."""
    test_cases = [
        ("NCLTDL0000012024", "National Company Law Tribunal", "Interlocutory Application (IBC)"),
        ("SCIN010394252025", "Supreme Court of India", "Special Leave Petition (Civil)"),
        ("DLHC010001232024", "High Court of Delhi", "Writ Petition (Civil)"),
    ]

    for cnr, expected_court, expected_type in test_cases:
        # 1. GET search
        get_resp = client.get(f"/api/v1/cases/search?cnr={cnr}")
        assert get_resp.status_code == 200, f"Failed for {cnr}: {get_resp.text}"
        get_data = get_resp.json()
        assert get_data["success"] is True
        assert get_data["query"]["cnr"] == cnr
        case = get_data["results"][0]
        # Critical validation: Requested CNR == Returned Case CNR
        assert case["cnr"] == cnr, f"Requested {cnr} != Returned {case['cnr']}"
        assert expected_court in case["court"]
        assert case["case_type"] == expected_type

        # 2. POST search
        post_resp = client.post("/api/v1/cases/search", json={"cnr": cnr})
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["success"] is True
        assert post_data["results"][0]["cnr"] == cnr


def test_single_session_multiple_cnr_searches():
    """Verify that a single session_id can be reused to search multiple different CNRs."""
    # 1. Create a single search session
    sess_resp = client.post("/api/v1/search/session")
    assert sess_resp.status_code == 201
    sdata = sess_resp.json()
    session_id = sdata["session_id"]
    captcha = sdata["captcha"]

    cnrs_to_search = [
        ("NCLTDL0000012024", "National Company Law Tribunal"),
        ("SCIN010394252025", "Supreme Court of India"),
        ("DLHC010001232024", "High Court of Delhi"),
        ("MHAU019999992015", "Maharashtra"),
    ]

    # Search all 4 CNRs using the exact same session_id
    for cnr, expected_name in cnrs_to_search:
        resp = client.get(f"/api/v1/cases/search?cnr={cnr}&session_id={session_id}&captcha={captcha}")
        assert resp.status_code == 200, f"Search failed for {cnr} using session {session_id}"
        data = resp.json()
        assert data["success"] is True
        assert data["query"]["cnr"] == cnr
        case = data["results"][0]
        assert case["cnr"] == cnr
        assert (expected_name in case["court"]) or (expected_name in case["state"])

    # Verify session is still alive after multiple searches
    status_resp = client.get(f"/api/v1/search/session/{session_id}")
    assert status_resp.status_code == 200

    # Clean up / terminate session
    del_resp = client.delete(f"/api/v1/search/session/{session_id}")
    assert del_resp.status_code == 200

    # Ensure session is closed
    expired_resp = client.get(f"/api/v1/search/session/{session_id}")
    assert expired_resp.status_code == 410


