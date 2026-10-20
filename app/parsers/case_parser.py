"""
Parser for eCourts HTML response pages and tables.
Converts case details tables, hearing timelines, and order links into normalized CaseDetails models.
"""

import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from app.schemas.case import (
    CaseDetails,
    CaseHistoryItem,
    OrderItem,
    DocumentItem,
    ActSectionItem,
    SubordinateCourtInfo,
)


def _clean_text(text: Optional[str]) -> str:
    """Strip whitespace and collapse multiple spaces/newlines."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_ecourts_case_html(html_content: str, default_cnr: str = "") -> Optional[CaseDetails]:
    """
    Parse the official eCourts case history HTML response.
    Extracts case info, status, parties, acts, hearing history, and orders.
    """
    if not html_content or ("Record Not Found" in html_content and "Case Details" not in html_content):
        return None

    soup = BeautifulSoup(html_content, "html.parser")

    # If the response explicitly states invalid captcha
    if "Invalid Captcha" in html_content or "captcha is invalid" in html_content.lower():
        from app.utils.exceptions import CaptchaInvalidException
        raise CaptchaInvalidException()

    # Extract all key-value label pairs from table rows
    field_map: Dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        # Standard 2-cell or 4-cell table structure
        for i in range(0, len(cells) - 1, 2):
            label = _clean_text(cells[i].get_text()).rstrip(":").lower()
            val = _clean_text(cells[i + 1].get_text())
            if label and val:
                field_map[label] = val

    # Primary identification
    cnr = field_map.get("cnr number") or field_map.get("cnr") or default_cnr
    if not cnr:
        # Try finding CNR via regex in the entire body
        cnr_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{4}[0-9]{10})\b", html_content)
        if cnr_match:
            cnr = cnr_match.group(1)

    case_type = field_map.get("case type")
    case_number = (
        field_map.get("case number")
        or field_map.get("registration number")
        or field_map.get("case no.")
    )
    filing_number = field_map.get("filing number") or field_map.get("filing no.")
    filing_date = field_map.get("filing date")
    registration_number = field_map.get("registration number") or field_map.get("reg. no.")
    registration_date = field_map.get("registration date") or field_map.get("reg. date")

    # Status & Dates
    status = field_map.get("case status") or field_map.get("status")
    first_hearing = field_map.get("first hearing date")
    next_hearing = field_map.get("decision date") or field_map.get("next hearing date")
    stage_of_case = field_map.get("stage of case") or field_map.get("case stage")
    disposal_nature = field_map.get("nature of disposal")
    court_and_judge = field_map.get("court number and judge") or field_map.get("coram")

    # Parties and Advocates
    petitioner = (
        field_map.get("petitioner")
        or field_map.get("petitioner and advocate")
        or field_map.get("appellant")
    )
    petitioner_advocate = field_map.get("advocate") or field_map.get("petitioner advocate")
    respondent = field_map.get("respondent") or field_map.get("respondent and advocate")
    respondent_advocate = field_map.get("respondent advocate")

    # Court & Location
    court_title = soup.find("h2") or soup.find("h3") or soup.find("h4")
    court_name = _clean_text(court_title.get_text()) if court_title else court_and_judge

    # Parse Case History Timeline
    history_items: List[CaseHistoryItem] = []
    for table in soup.find_all("table"):
        headers = [c.get_text().strip().lower() for c in table.find_all("th")]
        if any("business" in h or "hearing" in h or "purpose" in h for h in headers):
            judge_idx = next((i for i, h in enumerate(headers) if "judge" in h), None)
            business_idx = next((i for i, h in enumerate(headers) if "business" in h), None)
            hearing_idx = next((i for i, h in enumerate(headers) if "hearing" in h), None)
            purpose_idx = next((i for i, h in enumerate(headers) if "purpose" in h), None)

            for tr in table.find_all("tr")[1:]:
                tds = [_clean_text(td.get_text()) for td in tr.find_all("td")]
                if len(tds) >= 3:
                    judge_val = tds[judge_idx] if judge_idx is not None and judge_idx < len(tds) else None
                    business_val = tds[business_idx] if business_idx is not None and business_idx < len(tds) else None
                    hearing_val = tds[hearing_idx] if hearing_idx is not None and hearing_idx < len(tds) else None
                    purpose_val = tds[purpose_idx] if purpose_idx is not None and purpose_idx < len(tds) else None

                    history_items.append(
                        CaseHistoryItem(
                            judge=judge_val,
                            business_on_date=business_val,
                            hearing_date=hearing_val,
                            purpose_of_hearing=purpose_val,
                        )
                    )

    # Parse Orders and Judgments
    order_items: List[OrderItem] = []
    document_items: List[DocumentItem] = []
    for table in soup.find_all("table"):
        headers = [c.get_text().strip().lower() for c in table.find_all("th")]
        if any("order" in h or "judgment" in h for h in headers):
            for tr in table.find_all("tr")[1:]:
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    order_num = _clean_text(tds[0].get_text())
                    order_date = _clean_text(tds[1].get_text())
                    order_details = _clean_text(tds[2].get_text()) if len(tds) > 2 else ""

                    # Extract PDF download link if present
                    doc_link = tr.find("a")
                    doc_url = None
                    if doc_link and "href" in doc_link.attrs:
                        href = doc_link["href"]
                        if not href.startswith("javascript:"):
                            doc_url = href

                    order_item = OrderItem(
                        order_number=order_num,
                        order_date=order_date,
                        order_details=order_details,
                        document_url=doc_url,
                    )
                    order_items.append(order_item)

                    if doc_url:
                        document_items.append(
                            DocumentItem(
                                title=f"Order {order_num} ({order_date})",
                                document_type="Court Order PDF",
                                date=order_date,
                                url=doc_url,
                            )
                        )

    # Parse Acts and Sections
    acts: List[ActSectionItem] = []
    under_act = field_map.get("under act(s)") or field_map.get("act")
    under_section = field_map.get("under section(s)") or field_map.get("section")
    if under_act or under_section:
        acts.append(ActSectionItem(act=under_act, section=under_section))

    return CaseDetails(
        cnr=cnr or default_cnr,
        case_number=case_number,
        case_type=case_type,
        court=court_name,
        court_complex=field_map.get("court complex"),
        district=field_map.get("district"),
        state=field_map.get("state"),
        petitioner=petitioner,
        petitioner_advocate=petitioner_advocate,
        respondent=respondent,
        respondent_advocate=respondent_advocate,
        filing_number=filing_number,
        filing_date=filing_date,
        registration_number=registration_number,
        registration_date=registration_date,
        status=status,
        first_hearing_date=first_hearing,
        next_hearing_date=next_hearing,
        disposal_date=field_map.get("disposal date"),
        disposal_nature=disposal_nature,
        stage_of_case=stage_of_case,
        acts=acts,
        case_history=history_items,
        orders=order_items,
        documents=document_items,
    )
