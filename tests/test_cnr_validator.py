"""
Unit tests for CNR validator and parser.
"""

import pytest
from app.utils.cnr_validator import clean_cnr, is_valid_cnr, parse_cnr


def test_clean_cnr():
    assert clean_cnr(" mhau-01-999999-2015 ") == "MHAU019999992015"
    assert clean_cnr("DLHC01/000123/2021") == "DLHC010001232021"
    assert clean_cnr("") == ""
    assert clean_cnr(None) == ""


def test_valid_cnr():
    assert is_valid_cnr("MHAU019999992015") is True
    assert is_valid_cnr("DLHC010001232021") is True
    assert is_valid_cnr("KA01010000012020") is True
    assert is_valid_cnr("UP01020000552019") is True


def test_invalid_cnr():
    # Length errors
    assert is_valid_cnr("MHAU01999999201") is False   # 15 chars
    assert is_valid_cnr("MHAU0199999920155") is False # 17 chars

    # Unknown state code
    assert is_valid_cnr("ZZAU019999992015") is False

    # Invalid year
    assert is_valid_cnr("MHAU019999990999") is False
    assert is_valid_cnr("MHAU019999993000") is False

    # Non-digit case number
    assert is_valid_cnr("MHAU01ABCD992015") is False


def test_parse_cnr():
    parsed = parse_cnr("MHAU010001232015")
    assert parsed is not None
    assert parsed.state_code == "MH"
    assert parsed.state_name == "Maharashtra"
    assert parsed.district_code == "AU"
    assert parsed.establishment_code == "01"
    assert parsed.case_number == "123"
    assert parsed.case_year == 2015
