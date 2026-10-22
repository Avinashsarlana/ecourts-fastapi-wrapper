"""
CNR (Case Number Record) validation and parsing utility.
Implements the official 16-character alphanumeric specification established by e-Courts India.
Supports District Courts, High Courts, Supreme Court of India, and National Tribunals (NCLT, NGT, etc.).
"""

import re
from typing import NamedTuple, Optional


# Official state and UT code abbreviations used in Indian e-Courts CNR numbers
STATE_CODES = {
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DD": "Daman & Diu",
    "DH": "Dadra & Nagar Haveli",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu & Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LK": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Telangana",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
    "SC": "Supreme Court of India",
}

# Recognized specialized tribunals
TRIBUNAL_CODES = {
    "NCLT": "National Company Law Tribunal",
    "NGT": "National Green Tribunal",
    "DRT": "Debt Recovery Tribunal",
    "CAT": "Central Administrative Tribunal",
    "ITAT": "Income Tax Appellate Tribunal",
    "APTEL": "Appellate Tribunal for Electricity",
    "TDSAT": "Telecom Disputes Settlement and Appellate Tribunal",
}

# General 16-character alphanumeric CNR regex:
# Must start with a letter, contain 12 alphanumeric characters for jurisdiction/case, and end with a 4-digit filing year
CNR_GENERAL_REGEX = re.compile(r"^[A-Z][A-Z0-9]{11}[12][0-9]{3}$")


class CNRComponents(NamedTuple):
    raw_cnr: str
    state_code: str
    state_name: str
    district_code: str
    establishment_code: str
    case_number: str
    case_year: int
    court_type: str = "District Court"
    district_name: Optional[str] = None


def clean_cnr(cnr: str) -> str:
    """Normalize CNR string by stripping whitespace, hyphens, and slashes, converting to uppercase."""
    if not cnr:
        return ""
    return re.sub(r"[\s\-_/]", "", str(cnr)).strip().upper()


def is_valid_cnr(cnr: str) -> bool:
    """
    Check if the given string satisfies the official 16-character CNR format.
    Accepts valid 16-character alphanumeric codes ending in a 4-digit year,
    supporting District Courts, High Courts, Supreme Court, and National Tribunals.
    """
    if not cnr:
        return False
    cleaned = clean_cnr(cnr)
    if len(cleaned) != 16:
        return False
    if not CNR_GENERAL_REGEX.match(cleaned):
        return False
    try:
        year = int(cleaned[12:16])
        if year < 1900 or year > 2100:
            return False
    except ValueError:
        return False
    return True


def parse_cnr(cnr: str) -> Optional[CNRComponents]:
    """Parse a valid CNR into its individual structural components."""
    if not is_valid_cnr(cnr):
        return None
    cleaned = clean_cnr(cnr)

    # 1. Tribunal format (e.g., NCLTDL0000012024, NGT0010000012024)
    for trib_code, trib_name in TRIBUNAL_CODES.items():
        if cleaned.startswith(trib_code):
            bench_code = cleaned[len(trib_code):6]
            bench_names = {
                "DL": "New Delhi Bench",
                "MB": "Mumbai Bench",
                "CH": "Chandigarh Bench",
                "AH": "Ahmedabad Bench",
                "AL": "Allahabad Bench",
                "BL": "Bengaluru Bench",
                "HY": "Hyderabad Bench",
                "KL": "Kolkata Bench",
                "CT": "Cuttack Bench",
                "GH": "Guwahati Bench",
                "JP": "Jaipur Bench",
                "KC": "Kochi Bench",
                "IN": "Indore Bench",
                "AM": "Amaravati Bench",
            }
            bench_name = bench_names.get(bench_code, f"{bench_code} Bench" if bench_code else "Principal Bench")
            return CNRComponents(
                raw_cnr=cleaned,
                state_code=bench_code or trib_code,
                state_name=trib_name,
                district_code=bench_code,
                establishment_code="01",
                case_number=cleaned[6:12].lstrip("0") or "0",
                case_year=int(cleaned[12:16]),
                court_type="Tribunal",
                district_name=bench_name,
            )

    # 2. Supreme Court of India format (e.g., SCIN010394252025)
    if cleaned.startswith("SC"):
        return CNRComponents(
            raw_cnr=cleaned,
            state_code="SC",
            state_name="Supreme Court of India",
            district_code=cleaned[2:4],
            establishment_code=cleaned[4:6],
            case_number=cleaned[6:12].lstrip("0") or "0",
            case_year=int(cleaned[12:16]),
            court_type="Supreme Court",
            district_name="New Delhi",
        )

    # 3. High Court format (e.g., DLHC010001232024, MAB010001232024)
    state_abbr = cleaned[0:2]
    if cleaned[2:4] == "HC":
        state_title = STATE_CODES.get(state_abbr, state_abbr)
        return CNRComponents(
            raw_cnr=cleaned,
            state_code=state_abbr,
            state_name=state_title,
            district_code="HC",
            establishment_code=cleaned[4:6],
            case_number=cleaned[6:12].lstrip("0") or "0",
            case_year=int(cleaned[12:16]),
            court_type="High Court",
            district_name=f"High Court of {state_title}",
        )

    # 4. Standard District Court format and generic fallbacks
    state_title = STATE_CODES.get(state_abbr, "eCourts Establishment")
    dist_code = cleaned[2:4]
    return CNRComponents(
        raw_cnr=cleaned,
        state_code=state_abbr,
        state_name=state_title,
        district_code=dist_code,
        establishment_code=cleaned[4:6],
        case_number=cleaned[6:12].lstrip("0") or "0",
        case_year=int(cleaned[12:16]),
        court_type="District Court",
        district_name=dist_code,
    )
