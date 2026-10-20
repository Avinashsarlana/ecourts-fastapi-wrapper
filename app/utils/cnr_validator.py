"""
CNR (Case Number Record) validation and parsing utility.
Implements the official 16-character alphanumeric specification established by e-Courts India.
"""

import re
from typing import NamedTuple, Optional


# Official state code abbreviations used in Indian e-Courts CNR numbers
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
}

# Regex pattern for 16-char CNR:
# 2-letter state code + 2-letter/digit dist + 2-digit/char estab + 6-digit case no + 4-digit year
CNR_REGEX = re.compile(r"^([A-Z]{2})([A-Z0-9]{2})([A-Z0-9]{2})([0-9]{6})([12][0-9]{3})$")


class CNRComponents(NamedTuple):
    raw_cnr: str
    state_code: str
    state_name: str
    district_code: str
    establishment_code: str
    case_number: str
    case_year: int


def clean_cnr(cnr: str) -> str:
    """Normalize CNR string by stripping whitespace and converting to uppercase."""
    if not cnr:
        return ""
    # Remove hyphens, spaces, and special symbols sometimes entered by users
    return re.sub(r"[\s\-_/]", "", cnr).strip().upper()


def is_valid_cnr(cnr: str) -> bool:
    """Check if the given string satisfies the official 16-character CNR format."""
    cleaned = clean_cnr(cnr)
    if len(cleaned) != 16:
        return False
    match = CNR_REGEX.match(cleaned)
    if not match:
        return False
    state_code = match.group(1)
    # Check if the 2-letter state code is recognized
    return state_code in STATE_CODES


def parse_cnr(cnr: str) -> Optional[CNRComponents]:
    """Parse a valid CNR into its individual structural components."""
    cleaned = clean_cnr(cnr)
    match = CNR_REGEX.match(cleaned)
    if not match:
        return None
    state_code = match.group(1)
    state_name = STATE_CODES.get(state_code, "Unknown")
    return CNRComponents(
        raw_cnr=cleaned,
        state_code=state_code,
        state_name=state_name,
        district_code=match.group(2),
        establishment_code=match.group(3),
        case_number=match.group(4).lstrip("0") or "0",
        case_year=int(match.group(5)),
    )
