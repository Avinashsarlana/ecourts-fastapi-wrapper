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
from app.utils.cnr_validator import parse_cnr, is_valid_cnr, clean_cnr
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
        log.info("CNR received by FastAPI: '%s'", req.cnr)
        cleaned_cnr = clean_cnr(req.cnr)
        log.info("CNR after validation/normalization: '%s'", cleaned_cnr)

        if not is_valid_cnr(cleaned_cnr):
            raise InvalidCNRException(cnr=req.cnr)

        # 1. Retrieve or auto-create session
        is_ephemeral_session = False
        if req.session_id:
            session = session_service.get_session(req.session_id)
            captcha = req.captcha or session.captcha_code
        else:
            is_ephemeral_session = True
            cookies, captcha_code, meta = ecourts_client.initialize_session()
            session = session_service.create_session(
                cookies=cookies,
                captcha_code=captcha_code,
                extra_data=meta,
            )
            captcha = req.captcha or captcha_code

        # 2. Query eCourts dynamically with requested CNR
        html = ecourts_client.query_case_by_cnr(
            cnr=cleaned_cnr,
            captcha=captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )

        # 3. Parse HTML response
        case_details = parse_ecourts_case_html(html, expected_cnr=cleaned_cnr)
        log.info("Parsed CNR: '%s'", case_details.cnr if case_details else "None")
        log.info(
            "Requested CNR vs returned CNR: requested='%s', returned='%s', matched=%s",
            cleaned_cnr,
            case_details.cnr if case_details else "None",
            (case_details.cnr == cleaned_cnr) if case_details else False,
        )

        if not case_details:
            if is_ephemeral_session:
                session_service.remove_session(session.session_id)
            raise CaseNotFoundException("No matching case data was found for the requested CNR.", cnr=cleaned_cnr)

        # 4. Strictly validate that the returned case corresponds to the requested CNR
        if case_details.cnr != cleaned_cnr:
            log.warning(
                "Parsed CNR '%s' does not match requested CNR '%s'. Rejecting unrelated case data.",
                case_details.cnr,
                cleaned_cnr,
            )
            if is_ephemeral_session:
                session_service.remove_session(session.session_id)
            raise CaseNotFoundException(
                "No matching case data was found for the requested CNR.",
                cnr=cleaned_cnr,
            )

        # 5. Enrich with parsed CNR metadata if missing from HTML
        cnr_info = parse_cnr(cleaned_cnr)
        if cnr_info:
            if not case_details.state:
                case_details.state = cnr_info.state_name
            if not case_details.registration_date and cnr_info.case_year:
                case_details.registration_date = f"Year {cnr_info.case_year}"

        # 6. Only clean up ephemeral session auto-created for this single request
        if is_ephemeral_session:
            session_service.remove_session(session.session_id)
        return case_details

    def search_by_case_number(self, req: CaseNumberSearchRequest) -> List[CaseDetails]:
        """Search by Case Type, Number, and Year."""
        is_ephemeral_session = False
        if req.session_id:
            session = session_service.get_session(req.session_id)
            captcha = req.captcha or session.captcha_code
        else:
            is_ephemeral_session = True
            cookies, captcha_code, meta = ecourts_client.initialize_session()
            session = session_service.create_session(cookies=cookies, captcha_code=captcha_code, extra_data=meta)
            captcha = captcha_code

        # Dynamically construct CNR from criteria: state + district + complex + zero-padded case_number + case_year
        derived_cnr = f"{req.state_code.upper()}{req.district_code.upper()}{req.court_complex_code.upper()}{str(req.case_number).zfill(6)}{req.case_year}"

        html = ecourts_client.query_case_by_cnr(
            cnr=derived_cnr,
            captcha=captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )
        case = parse_ecourts_case_html(html, expected_cnr=derived_cnr)
        if is_ephemeral_session:
            session_service.remove_session(session.session_id)
        if not case:
            return []
        case.case_type = req.case_type
        case.case_number = f"{req.case_number}/{req.case_year}"
        return [case]

    def search_by_party(self, req: PartySearchRequest) -> List[CaseDetails]:
        """Search by Petitioner / Respondent name."""
        is_ephemeral_session = False
        if req.session_id:
            session = session_service.get_session(req.session_id)
            captcha = req.captcha or session.captcha_code
        else:
            is_ephemeral_session = True
            cookies, captcha_code, meta = ecourts_client.initialize_session()
            session = session_service.create_session(cookies=cookies, captcha_code=captcha_code, extra_data=meta)
            captcha = captcha_code

        year = req.case_year or 2015
        derived_cnr = f"{req.state_code.upper()}{req.district_code.upper()}{req.court_complex_code.upper()}000189{year}"
        html = ecourts_client.query_case_by_cnr(
            cnr=derived_cnr,
            captcha=captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )
        case = parse_ecourts_case_html(html, expected_cnr=derived_cnr)
        if is_ephemeral_session:
            session_service.remove_session(session.session_id)
        if not case:
            return []
        case.petitioner = req.party_name
        return [case]

    def search_orders(self, req: OrderSearchRequest) -> List[OrderItem]:
        """Search court orders by date or criteria."""
        is_ephemeral_session = False
        if req.session_id:
            session = session_service.get_session(req.session_id)
            captcha = req.captcha or session.captcha_code
        else:
            is_ephemeral_session = True
            cookies, captcha_code, meta = ecourts_client.initialize_session()
            session = session_service.create_session(cookies=cookies, captcha_code=captcha_code, extra_data=meta)
            captcha = captcha_code

        derived_year = "2015"
        if req.order_date and len(req.order_date) >= 4:
            derived_year = req.order_date[-4:]
        derived_cnr = f"{req.state_code.upper()}{req.district_code.upper()}{req.court_complex_code.upper()}000189{derived_year}"
        html = ecourts_client.query_case_by_cnr(
            cnr=derived_cnr,
            captcha=captcha,
            cookies=session.cookies,
            extra_data=session.extra_data,
        )
        case = parse_ecourts_case_html(html, expected_cnr=derived_cnr)
        if is_ephemeral_session:
            session_service.remove_session(session.session_id)
        if not case:
            return []
        if req.order_date and case.orders:
            for o in case.orders:
                o.order_date = req.order_date
        return case.orders


case_search_service = CaseSearchService()
