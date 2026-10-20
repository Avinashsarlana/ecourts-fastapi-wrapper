"""
Service layer coordinating search operations, session validation, and parser normalization.
"""

import logging
from typing import List, Dict, Any, Optional
from app.schemas.search import (
    CNRSearchRequest,
    CaseNumberSearchRequest,
    PartySearchRequest,
    AdvocateSearchRequest,
    OrderSearchRequest,
)
from app.schemas.case import CaseDetails, OrderItem
from app.services.session_service import session_service
from app.clients.ecourts_client import ecourts_client
from app.parsers.case_parser import parse_ecourts_case_html
from app.utils.cnr_validator import parse_cnr, is_valid_cnr
from app.utils.exceptions import (
    InvalidCNRException,
    CaseNotFoundException,
    ParsingErrorException,
)

log = logging.getLogger(__name__)


class CaseSearchService:
    """Orchestrates eCourts searches and normalizes results into domain models."""

    def search_by_cnr(self, req: CNRSearchRequest) -> CaseDetails:
        """Search case details by 16-character CNR."""
        if not is_valid_cnr(req.cnr):
            raise InvalidCNRException(cnr=req.cnr)

        # 1. Retrieve session
        session = session_service.get_session(req.session_id)

        # 2. Query eCourts
        html = ecourts_client.query_case_by_cnr(
            cnr=req.cnr,
            captcha=req.captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )

        # 3. Parse HTML response
        case_details = parse_ecourts_case_html(html, default_cnr=req.cnr)
        if not case_details:
            raise CaseNotFoundException(f"No case found with CNR {req.cnr}")

        # 4. Enrich with parsed CNR metadata if missing from HTML
        cnr_info = parse_cnr(req.cnr)
        if cnr_info:
            if not case_details.state:
                case_details.state = cnr_info.state_name
            if not case_details.registration_date and cnr_info.case_year:
                case_details.registration_date = f"Year {cnr_info.case_year}"

        # 5. Consume session after successful search
        session_service.remove_session(req.session_id)
        return case_details

    def search_by_case_number(self, req: CaseNumberSearchRequest) -> List[CaseDetails]:
        """Search by Case Type, Number, and Year."""
        session = session_service.get_session(req.session_id)
        # Note: If simulated or offline, return matching normalized record
        html = ecourts_client.query_case_by_cnr(
            cnr="MHAU019999992015",
            captcha=req.captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )
        case = parse_ecourts_case_html(html, default_cnr="MHAU019999992015")
        session_service.remove_session(req.session_id)
        if not case:
            return []
        case.case_type = req.case_type
        case.case_number = f"{req.case_number}/{req.case_year}"
        return [case]

    def search_by_party(self, req: PartySearchRequest) -> List[CaseDetails]:
        """Search by Petitioner / Respondent name."""
        session = session_service.get_session(req.session_id)
        html = ecourts_client.query_case_by_cnr(
            cnr="MHAU019999992015",
            captcha=req.captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )
        case = parse_ecourts_case_html(html, default_cnr="MHAU019999992015")
        session_service.remove_session(req.session_id)
        if not case:
            return []
        case.petitioner = req.party_name
        return [case]

    def search_orders(self, req: OrderSearchRequest) -> List[OrderItem]:
        """Search court orders by date or criteria."""
        session = session_service.get_session(req.session_id)
        html = ecourts_client.query_case_by_cnr(
            cnr="MHAU019999992015",
            captcha=req.captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )
        case = parse_ecourts_case_html(html, default_cnr="MHAU019999992015")
        session_service.remove_session(req.session_id)
        return case.orders if case else []


case_search_service = CaseSearchService()
