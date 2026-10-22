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
    base_url = "https://ecourtsindia.com"
    assert len(case.orders) == 3
    assert case.orders[0].order_number == "Order 1"
    assert case.orders[0].document_url == f"{base_url}/orders/2015/order_1.pdf"
    assert len(case.documents) == 3
    assert case.documents[-1].url == f"{base_url}/orders/2021/final_decree.pdf"
    assert case.portal_url == f"{base_url}/cnr/MHAU019999992015"

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


def test_parse_dlhc_case_html():
    from app.clients.ecourts_client import generate_mock_case_html
    html = generate_mock_case_html("DLHC010001232024")
    case = parse_ecourts_case_html(html, expected_cnr="DLHC010001232024")
    assert case is not None
    assert case.cnr == "DLHC010001232024"
    assert "Delhi" in case.court
    assert case.petitioner == "Shubham Pratap Singh"
    assert case.respondent == "Kendriya Vidyalaya Sangathan (Kvs) & Ors"
    assert case.case_type == "Writ Petition (Civil)"
    assert case.portal_url == "https://ecourtsindia.com/cnr/DLHC010001232024"


def test_parse_ecourtsindia_json_ld():
    from app.parsers.case_parser import parse_ecourtsindia_html
    sample_html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Article",
      "identifier": "DLHC010001232024",
      "headline": "Writ Petition (Civil) - Shubham Pratap Singh vs Kendriya Vidyalaya Sangathan (Kvs) & Ors",
      "author": {"@type": "Person", "name": "Hon'ble Tushar Rao Gedela"},
      "publisher": {"@type": "Organization", "name": "High Court of Delhi, Delhi"},
      "about": [{
        "@type": "LegalCase",
        "caseNumber": "138/2024",
        "legislationApplies": "Writ Petition (Civil)",
        "legalStatus": "Disposed",
        "court": "High Court of Delhi, Delhi",
        "plaintiff": {"@type": "Person", "name": "Shubham Pratap Singh"},
        "defendant": {"@type": "Person", "name": "Kendriya Vidyalaya Sangathan (Kvs) & Ors"},
        "dateFiled": "2024-01-04"
      }],
      "citation": [{
        "@type": "CreativeWork",
        "name": "Final Order",
        "url": "https://ecourtsindia.com/cnr/DLHC010001232024/order-1",
        "datePublished": "2024-01-05"
      }]
    }
    </script>
    </head>
    <body>
      <h1>Shubham Pratap Singh vs. Kendriya Vidyalaya Sangathan (Kvs) &amp; Ors</h1>
      <div id="timeline">
        <div class="hidden sm:flex"><div>5 Jan 2024</div><div>Disposed</div><div>Final Order</div></div>
      </div>
    </body>
    </html>
    """
    case = parse_ecourtsindia_html(sample_html, target_cnr="DLHC010001232024")
    assert case is not None
    assert case.cnr == "DLHC010001232024"
    assert case.petitioner == "Shubham Pratap Singh"
    assert case.respondent == "Kendriya Vidyalaya Sangathan (Kvs) & Ors"
    assert case.court == "High Court of Delhi, Delhi"
    assert case.status == "DISPOSED"
    assert len(case.orders) == 1
    assert case.orders[0].document_url == "https://ecourtsindia.com/cnr/DLHC010001232024/order-1"
    assert case.portal_url == "https://ecourtsindia.com/cnr/DLHC010001232024"

