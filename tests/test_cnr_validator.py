"""
Unit tests for CNR validator and parser across District Courts, High Courts, Supreme Court, and Tribunals.
"""

import pytest
from app.utils.cnr_validator import clean_cnr, is_valid_cnr, parse_cnr


def test_clean_cnr():
    assert clean_cnr(" mhau-01-999999-2015 ") == "MHAU019999992015"
    assert clean_cnr("DLHC01/000123/2021") == "DLHC010001232021"
    assert clean_cnr("NCLT-DL-000001-2024") == "NCLTDL0000012024"
    assert clean_cnr("SC_IN01_039425_2025") == "SCIN010394252025"
    assert clean_cnr("") == ""
    assert clean_cnr(None) == ""


def test_valid_cnr():
    # User-tested CNRs from various courts
    assert is_valid_cnr("NCLTDL0000012024") is True  # National Company Law Tribunal
    assert is_valid_cnr("SCIN010394252025") is True  # Supreme Court of India
    assert is_valid_cnr("DLHC010001232024") is True  # Delhi High Court

    # Standard District Courts
    assert is_valid_cnr("MHAU019999992015") is True
    assert is_valid_cnr("DLHC010001232021") is True
    assert is_valid_cnr("KA01010000012020") is True
    assert is_valid_cnr("UP01020000552019") is True


def test_invalid_cnr():
    # Length errors
    assert is_valid_cnr("MHAU01999999201") is False    # 15 chars
    assert is_valid_cnr("MHAU0199999920155") is False  # 17 chars
    assert is_valid_cnr("") is False
    assert is_valid_cnr(None) is False

    # Invalid characters or start
    assert is_valid_cnr("1234567890123456") is False  # Starts with digit
    assert is_valid_cnr("@#$$%^&*()!@#2024") is False  # Special chars

    # Invalid year
    assert is_valid_cnr("MHAU019999990999") is False
    assert is_valid_cnr("MHAU019999993000") is False


def test_parse_cnr_district_court():
    parsed = parse_cnr("MHAU010001232015")
    assert parsed is not None
    assert parsed.state_code == "MH"
    assert parsed.state_name == "Maharashtra"
    assert parsed.district_code == "AU"
    assert parsed.establishment_code == "01"
    assert parsed.case_number == "123"
    assert parsed.case_year == 2015
    assert parsed.court_type == "District Court"


def test_parse_cnr_tribunal():
    parsed = parse_cnr("NCLTDL0000012024")
    assert parsed is not None
    assert parsed.state_name == "National Company Law Tribunal"
    assert parsed.court_type == "Tribunal"
    assert "New Delhi Bench" in parsed.district_name
    assert parsed.case_number == "1"
    assert parsed.case_year == 2024


def test_parse_cnr_supreme_court():
    parsed = parse_cnr("SCIN010394252025")
    assert parsed is not None
    assert parsed.state_name == "Supreme Court of India"
    assert parsed.court_type == "Supreme Court"
    assert parsed.case_number == "39425"
    assert parsed.case_year == 2025


def test_parse_cnr_high_court():
    parsed = parse_cnr("DLHC010001232024")
    assert parsed is not None
    assert parsed.state_name == "Delhi"
    assert parsed.court_type == "High Court"
    assert parsed.case_number == "123"
    assert parsed.case_year == 2024
