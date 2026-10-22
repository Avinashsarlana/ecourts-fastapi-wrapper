"""
Parser for eCourts HTML response pages and tables.
Converts case details tables, hearing timelines, and order links into normalized CaseDetails models.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from app.config.settings import settings
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


def parse_ecourtsindia_html(html_content: str, target_cnr: str = "") -> Optional[CaseDetails]:
    """
    Parse page HTML and JSON-LD from eCourts India (https://ecourtsindia.com/cnr/<cnr>).
    Extracts authentic case metadata, parties, advocates, timeline history, and order documents.
    """
    if not html_content or ("404" in html_content and "not found" in html_content.lower() and "Shubham" not in html_content):
        return None

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Parse JSON-LD structured data if present
    json_ld = None
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(s.string)
            if isinstance(d, dict) and d.get("@type") == "Article" and d.get("identifier"):
                json_ld = d
                break
        except Exception:
            pass

    if not json_ld and not soup.find("h1") and "timeline" not in html_content:
        return None

    author = json_ld.get("author", {}).get("name") if json_ld and isinstance(json_ld.get("author"), dict) else None
    publisher = json_ld.get("publisher", {}).get("name") if json_ld and isinstance(json_ld.get("publisher"), dict) else None

    about_list = json_ld.get("about", []) if json_ld else []
    about = about_list[0] if (about_list and isinstance(about_list, list)) else {}

    case_number = about.get("caseNumber")
    case_type = about.get("legislationApplies")
    status = about.get("legalStatus")
    court = about.get("court") or publisher
    filing_date = about.get("dateFiled")

    plaintiff = about.get("plaintiff", {}).get("name") if isinstance(about.get("plaintiff"), dict) else None
    defendant = about.get("defendant", {}).get("name") if isinstance(about.get("defendant"), dict) else None

    # 2. Extract key-value span data from page header
    span_data: Dict[str, str] = {}
    for s in soup.find_all("span"):
        txt = _clean_text(s.get_text()).rstrip(":").lower()
        if txt in ["court", "judge", "case type", "reg no", "filing no", "cnr", "judicial section"]:
            nxt = s.find_next_sibling()
            if nxt and txt not in span_data:
                span_data[txt] = _clean_text(nxt.get_text())

    # Only override court from span if span is specific
    if span_data.get("court") and span_data.get("court") != "High Court":
        court = span_data.get("court")
    judge_name = span_data.get("judge") or author
    case_type = span_data.get("case type") or case_type
    registration_number = span_data.get("reg no") or case_number
    filing_number = span_data.get("filing no")
    cnr_val = span_data.get("cnr") or (json_ld.get("identifier") if json_ld else None) or target_cnr

    # 3. Extract Parties & Advocates from H3 sections
    petitioner = plaintiff
    petitioner_adv = None
    respondent = defendant
    respondent_adv = None

    for h3 in soup.find_all("h3"):
        h3_text = _clean_text(h3.get_text()).lower()
        parent = h3.find_parent("div")
        if not parent:
            continue
        names = []
        for row in parent.find_all("div", class_=re.compile(r"bg-gray-50")):
            val = _clean_text(row.get_text(separator=" "))
            val = re.sub(r"^\d+\s*", "", val).strip()
            if val:
                names.append(val)
        joined_names = ", ".join(names) if names else None

        if "petitioner advocate" in h3_text:
            petitioner_adv = joined_names
        elif "petitioner" in h3_text and joined_names:
            petitioner = joined_names
        elif "respondent advocate" in h3_text:
            respondent_adv = joined_names
        elif "respondent" in h3_text and joined_names:
            respondent = joined_names

    # Fallback to H1 title parsing (e.g., "Petitioner vs. Respondent")
    if not petitioner:
        h1 = soup.find("h1")
        if h1:
            h1_text = _clean_text(h1.get_text())
            if " vs." in h1_text:
                parts = h1_text.split(" vs.")
                petitioner = parts[0].strip()
                if not respondent and len(parts) > 1:
                    respondent = parts[1].strip()
            elif " vs " in h1_text:
                parts = h1_text.split(" vs ")
                petitioner = parts[0].strip()
                if not respondent and len(parts) > 1:
                    respondent = parts[1].strip()

    # 4. Extract Subordinate Court info
    sub_court = None
    prev = about.get("previousCourt")
    if prev and isinstance(prev, dict):
        sub_court = SubordinateCourtInfo(
            court_name=prev.get("name"),
            case_number=prev.get("caseNumber"),
            decision_date=prev.get("decisionDate"),
        )

    # 5. Extract Orders and Documents
    order_items: List[OrderItem] = []
    document_items: List[DocumentItem] = []
    citations = json_ld.get("citation", []) if json_ld else []
    for i, cit in enumerate(citations):
        name = cit.get("name") or f"Order {i+1}"
        date_pub = cit.get("datePublished")
        url = cit.get("url")
        order_items.append(
            OrderItem(
                order_number=name,
                order_date=date_pub,
                order_details=name,
                document_url=url,
            )
        )
        if url:
            document_items.append(
                DocumentItem(
                    title=f"{name} ({date_pub})" if date_pub else name,
                    document_type="Court Order",
                    date=date_pub,
                    url=url,
                )
            )

    # If no citation in JSON-LD, look for order links in HTML
    if not order_items:
        for a in soup.find_all("a", href=True):
            if "/order" in a["href"]:
                txt = _clean_text(a.get_text(separator=" "))
                href = a["href"]
                doc_url = f"https://ecourtsindia.com{href}" if href.startswith("/") else href
                order_items.append(
                    OrderItem(
                        order_number="Order",
                        order_date=None,
                        order_details=txt,
                        document_url=doc_url,
                    )
                )
                document_items.append(
                    DocumentItem(
                        title=txt or "Court Order",
                        document_type="Court Order",
                        date=None,
                        url=doc_url,
                    )
                )

    # 6. Extract Timeline / Case History
    history_items: List[CaseHistoryItem] = []
    first_hearing = None
    next_hearing = None
    disposal_date = None
    disposal_nature = None

    timeline = soup.find(id="timeline")
    if timeline:
        for row in timeline.find_all("div", class_=re.compile(r"hidden sm:flex")):
            txts = [t.strip() for t in row.stripped_strings]
            if len(txts) >= 2:
                date_candidate = txts[0]
                stage = txts[1]
                purpose = " ".join(txts[2:]) if len(txts) > 2 else stage

                if "disposed" in date_candidate.lower() or "disposed" in stage.lower():
                    status = "Disposed"
                    disposal_nature = stage
                    m = re.search(r"(\d+\s+[A-Za-z]+\s+\d{4})", date_candidate)
                    if m:
                        disposal_date = m.group(1)
                elif "first hearing" in stage.lower() or "first hearing" in purpose.lower():
                    first_hearing = date_candidate
                elif not next_hearing and any(char.isdigit() for char in date_candidate):
                    next_hearing = date_candidate

                history_items.append(
                    CaseHistoryItem(
                        hearing_date=date_candidate,
                        business_on_date=date_candidate,
                        purpose_of_hearing=purpose,
                        judge=judge_name,
                    )
                )

    # State & District inference
    state = None
    district = None
    if court:
        if "Delhi" in court:
            state = "Delhi"
        elif "TELANGANA" in court or "Telangana" in court:
            state = "Telangana"
        elif "Maharashtra" in court:
            state = "Maharashtra"

    base_url = settings.ECOURTS_SERVICES_BASE_URL.rstrip("/")
    portal_url = f"{base_url}/cnr/{cnr_val}"

    return CaseDetails(
        cnr=cnr_val,
        case_number=case_number or registration_number,
        case_type=case_type,
        court=court,
        court_complex=None,
        district=district,
        state=state,
        petitioner=petitioner,
        petitioner_advocate=petitioner_adv,
        respondent=respondent,
        respondent_advocate=respondent_adv,
        filing_number=filing_number,
        filing_date=filing_date,
        registration_number=registration_number,
        registration_date=filing_date,
        status=status.upper() if status else None,
        first_hearing_date=first_hearing,
        next_hearing_date=next_hearing,
        disposal_date=disposal_date,
        disposal_nature=disposal_nature,
        stage_of_case=status,
        portal_url=portal_url,
        acts=[],
        subordinate_court=sub_court,
        case_history=history_items,
        orders=order_items,
        documents=document_items,
    )


def parse_ecourts_case_html(
    html_content: str,
    default_cnr: str = "",
    expected_cnr: str = "",
) -> Optional[CaseDetails]:
    """
    Parse eCourts case history HTML response.
    Supports official eCourts table layout and eCourts India modern layout.
    """
    target_cnr = expected_cnr or default_cnr

    # If the response is from eCourts India (JSON-LD, timeline, or React components)
    if html_content and (
        "application/ld+json" in html_content
        or "timeline" in html_content
        or "ecourtsindia" in html_content
        or "Parties & Advocates" in html_content
    ):
        ec_case = parse_ecourtsindia_html(html_content, target_cnr=target_cnr)
        if ec_case:
            return ec_case

    if not html_content or (
        (
            "Record Not Found" in html_content
            or "does not exists" in html_content
            or "something wrong" in html_content.lower()
            or "invalid request" in html_content.lower()
            or "errormsg" in html_content
        )
        and "Case Details" not in html_content
        and "case_details_table" not in html_content
    ):
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

    # If no key-value fields could be parsed and no tables exist, this is not a valid case response
    if not field_map and not soup.find("table"):
        return None

    # Primary identification
    cnr = (
        field_map.get("cnr number")
        or field_map.get("cnr")
        or field_map.get("cino")
        or field_map.get("cnr no.")
        or field_map.get("cnr no")
    )
    if not cnr:
        # Try finding CNR via regex in the entire body
        cnr_match = re.search(r"\b([A-Z][A-Z0-9]{11}[12][0-9]{3})\b", html_content)
        if cnr_match:
            cnr = cnr_match.group(1)
    if not cnr:
        cnr = target_cnr

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
                            base_url = settings.ECOURTS_SERVICES_BASE_URL.rstrip("/")
                            if href.startswith("http://") or href.startswith("https://"):
                                if "services.ecourts.gov.in" in href and "ecourtsindia.com" in base_url:
                                    doc_url = href.replace("https://services.ecourts.gov.in", base_url).replace("http://services.ecourts.gov.in", base_url)
                                else:
                                    doc_url = href
                            else:
                                doc_url = f"{base_url}{href if href.startswith('/') else '/' + href}"

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

    final_cnr = cnr or target_cnr
    base_url = settings.ECOURTS_SERVICES_BASE_URL.rstrip("/")
    portal_url = f"{base_url}/cnr/{final_cnr}" if final_cnr else None

    return CaseDetails(
        cnr=final_cnr,
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
        portal_url=portal_url,
        acts=acts,
        case_history=history_items,
        orders=order_items,
        documents=document_items,
    )
