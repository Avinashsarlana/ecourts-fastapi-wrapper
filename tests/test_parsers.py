"""
Unit tests for eCourts HTML response parsers.
"""

import pytest
from app.parsers.case_parser import parse_ecourts_case_html
from app.clients.ecourts_client import MOCK_CASE_HTML
from app.utils.exceptions import CaptchaInvalidException


def test_parse_valid_case_html():
    case = parse_ecourts_case_html(MOCK_CASE_HTML, default_cnr="MHAU019999992015")
    assert case is not None
    assert case.cnr == "MHAU019999992015"
    assert case.case_type == "Special Civil Suit (SCS)"
    assert case.case_number == "000189/2015"
    assert case.filing_number == "000452/2015"
    assert case.filing_date == "14-04-2015"
    assert case.registration_date == "22-04-2015"
    assert case.status == "DISPOSED"
    assert case.disposal_nature == "Decreed in favour of Plaintiff"
    assert "Patil" in case.petitioner
    assert "Maharashtra State Electricity" in case.respondent

    # Verify history timeline
    assert len(case.case_history) == 6
    assert case.case_history[0].hearing_date == "05-05-2015"
    assert case.case_history[-1].purpose_of_hearing == "Judgment & Decree Announced"

    # Verify orders and document PDF links
    assert len(case.orders) == 3
    assert case.orders[0].order_number == "Order 1"
    assert case.orders[0].document_url == "https://services.ecourts.gov.in/orders/2015/order_1.pdf"
    assert len(case.documents) == 3
    assert case.documents[-1].url == "https://services.ecourts.gov.in/orders/2021/final_decree.pdf"

    # Verify statutory acts
    assert len(case.acts) == 1
    assert "Code of Civil Procedure" in case.acts[0].act


def test_parse_captcha_invalid_html():
    html = "<div><span class='error'>Invalid Captcha code entered</span></div>"
    with pytest.raises(CaptchaInvalidException):
        parse_ecourts_case_html(html)


def test_parse_not_found_html():
    html = "<div><span>Record Not Found for the given CNR</span></div>"
    assert parse_ecourts_case_html(html) is None
