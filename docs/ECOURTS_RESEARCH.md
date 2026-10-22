# Comprehensive Research: eCourts Public Services, Portals & System Architecture

This document provides technical documentation on India's **eCourts Services** ecosystem and the modern **eCourts India Portal** (`ecourtsindia.com`), detailing public search capabilities, session dynamics, CAPTCHA mechanisms, parameters, and machine-readable data structures.

---

## 1. Executive Summary & Overview of Platforms

India's judicial digitisation operates under the e-Committee of the Supreme Court of India, the Department of Justice, and public legal tech interfaces. Case status, daily orders, cause lists, and final judgments are accessible across multiple key portals:

| Platform | Primary Domain | Target Jurisdiction | Backend System |
|---|---|---|---|
| **eCourts India Portal** | `ecourtsindia.com` | District, High Court, Supreme Court & Tribunals | Modern React/Next.js & JSON-LD legal schema |
| **District Court Services** | `services.ecourts.gov.in` | District & Taluka Courts across 36 States/UTs | CIS (Case Information System) 3.2 / PHP |
| **High Court Services** | `hcservices.ecourts.gov.in` | 25 State High Courts & respective Benches | CIS High Court National Core |
| **eCourts Judgment Search** | `judgments.ecourts.gov.in` | High Courts & Supreme Court Judgments | Elastic / Solr backed full-text index |

---

## 2. Official Machine-Readable Interfaces & API Availability

### Platform Investigation:
1. **Public REST APIs**: The official public portals (`services.ecourts.gov.in`, `judgments.ecourts.gov.in`) **do not provide an open, unauthenticated public REST API without CAPTCHA** for commercial or general public third-party access.
2. **eCourts India Modern Portal (`ecourtsindia.com`)**: Serves structured legal case data embedded in `application/ld+json` (`Schema.org/LegalCase`, `Schema.org/Article`) and timeline HTML elements, with direct case URLs of the form `https://ecourtsindia.com/cnr/{CNR}`.
3. **eCourts Mobile App APIs**: Utilizes HTTPS endpoints backed by session tokens, device signatures, and server-side rate-limiting.
4. **Judicial Data Exchange**: Government departments access feeds via dedicated secure gateways (e.g., NSTEP, ICJS) requiring pre-authorized credentials and IP whitelisting.

### Wrapper Architectural Decision:
The FastAPI wrapper implements a resilient dual-engine strategy:
* Direct lookup via `curl_cffi` (Chrome impersonation) for `ecourtsindia.com` JSON-LD and timeline elements.
* State-managed session workflow (`/api/v1/search/session`) for traditional portal integration with permitted human-in-the-loop CAPTCHA resolution.
* Offline mock fallback mode for development and test automation.

---

## 3. CNR (Case Number Record) Specifications Across Judicial Tiers

The **CNR Number** is the unique 16-character alphanumeric identifier assigned to court cases throughout India.

### 1. District Court Format:
Example: `MHAU010001892015`

```
  MH      AU        01          000189         2015
[State] [Dist] [Establishment] [Case Number] [Filing Year]
```

* **State Code (Chars 1–2)**: 2-letter postal code (e.g., `MH` = Maharashtra, `DL` = Delhi, `KA` = Karnataka, `UP` = Uttar Pradesh).
* **District Code (Chars 3–4)**: 2-character district code (e.g., `AU` = Aurangabad, `SW` = South West Delhi).
* **Establishment Code (Chars 5–6)**: 2-character code identifying the specific court complex within the district.
* **Case Number (Chars 7–12)**: 6 digits, zero-padded case filing sequence number.
* **Year (Chars 13–16)**: 4-digit filing year (e.g., `2015`).

### 2. High Court Format:
Example: `DLHC010001232024`
* **Chars 1–2**: State abbreviation (e.g., `DL` = Delhi, `MH` = Bombay).
* **Chars 3–4**: `HC` designating High Court.
* **Chars 5–6**: Bench or establishment identifier (e.g., `01` = Principal Bench).
* **Chars 7–12**: 6-digit zero-padded case number (`000123`).
* **Chars 13–16**: 4-digit filing year (`2024`).

### 3. Supreme Court of India Format:
Example: `SCIN010394252025`
* **Chars 1–2**: `SC` designating Supreme Court.
* **Chars 3–4**: `IN` designating India national jurisdiction.
* **Chars 5–6**: Establishment / Section code (`01`).
* **Chars 7–12**: 6-digit Diary / Case sequence (`039425`).
* **Chars 13–16**: 4-digit year (`2025`).

### 4. Specialized National Tribunals Format:
Examples: `NCLTDL0000012024`, `NGT0010000012024`
* **Prefix**: Recognized tribunal codes (`NCLT`, `NGT`, `DRT`, `CAT`, `ITAT`, `APTEL`, `TDSAT`).
* **Bench Code**: e.g., `DL` (New Delhi Bench), `MB` (Mumbai Bench), etc.
* **Sequence & Year**: 6-digit sequence number followed by a 4-digit filing year.

---

## 4. Secondary Search Modes

When the CNR is unknown, the wrapper supports secondary search criteria:

| Search Type | Parameters Required | Return Information |
|---|---|---|
| **Case Number** | `state_code`, `dist_code`, `court_complex_code`, `case_type`, `case_number`, `case_year` | Single matching case details and history |
| **Party Name** | `state_code`, `dist_code`, `court_complex_code`, `party_name`, `case_year`, `status` (Pending/Disposed/Both) | List of matching cases with petitioner/respondent names |
| **Advocate Name** | `state_code`, `dist_code`, `court_complex_code`, `advocate_name`, `case_year` | List of cases represented by the advocate |
| **Court Orders** | `state_code`, `dist_code`, `court_complex_code`, `order_date`, `court_number`, `party_name` | Table of interim and final orders with PDF links |

---

## 5. CAPTCHA Handling & Session Lifecycle Design

### Session Management:
* **Creation**: `POST /api/v1/search/session` initiates a session, retrieves cookies, and resolves the CAPTCHA challenge.
* **Status**: `GET /api/v1/search/session/{session_id}` inspects time-to-live and current session state.
* **Termination**: `DELETE /api/v1/search/session/{session_id}` immediately cleans up the session store upon batch completion.
* **Expiration**: Default TTL of 600 seconds (10 minutes) with automatic background pruning of expired keys.

### Workflow Diagram:

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / User
    participant API as FastAPI Wrapper
    participant Store as Session Store (TTL 10m)
    participant Portal as eCourts Portal

    User->>API: POST /api/v1/search/session
    API->>Portal: GET /?p=casestatus/cnr (Acquire session cookies)
    API->>Store: Store session cookies & captcha state
    API-->>User: Return session_id & captcha code
    
    User->>API: POST /api/v1/cases/search {session_id, captcha, cnr}
    API->>Store: Validate active session
    API->>Portal: Fetch Case (cino_qry.php or /cnr/{cnr})
    Portal-->>API: Return HTML / JSON-LD data
    API->>API: Parse & normalize to CaseDetails JSON
    API-->>User: Return structured CaseDetails
    
    User->>API: DELETE /api/v1/search/session/{session_id}
    API->>Store: Remove session from memory
    API-->>User: Confirmation {success: true}
```

---

## 6. Response Normalization & Schema Mapping

The wrapper normalizes unstructured HTML responses into structured `CaseDetails` models:

| Source Field in Portal | Normalized Field in `CaseDetails` | Type | Description |
|---|---|---|---|
| `CNR Number` / `cino` | `cnr` | `str` (16 chars) | Unique Case Number Record |
| `Case Type` | `case_type` | `str` | e.g., Writ Petition, Civil Suit |
| `Filing Number` / `Filing Date` | `filing_number`, `filing_date` | `str` | Initial filing reference |
| `Registration Number` / `Date` | `registration_number`, `registration_date` | `str` | Formal court registration |
| `Case Status` / `Nature of Disposal`| `status`, `disposal_nature` | `str` | Current status (PENDING / DISPOSED) |
| `First Hearing` / `Next Hearing` | `first_hearing_date`, `next_hearing_date` | `str` | Hearing schedule |
| `Petitioner` / `Advocate` | `petitioner`, `petitioner_advocate` | `str` | Primary petitioner and legal counsel |
| `Respondent` / `Advocate` | `respondent`, `respondent_advocate` | `str` | Opposing party and counsel |
| `Court Number and Judge` | `court` | `str` | Presiding coram and court room |
| Direct Web Link | `portal_url` | `str` | Direct URL to view case on portal |
| `Under Act(s)` / `Section(s)` | `acts` | `List[ActSectionItem]` | Statutory acts and sections |
| `Business on Date` / Timeline | `case_history` | `List[CaseHistoryItem]` | Hearing history and stage |
| `Orders` / Documents | `orders` & `documents` | `List[OrderItem]`, `List[DocumentItem]` | Order dates, details & PDF links |

---

## 7. Status of Functionality & Roadmap

* **Confirmed & Fully Verified (30/30 Tests Passing)**:
  - Multi-tier CNR validation & parsing (District Courts, High Courts, Supreme Court, Tribunals).
  - Dual-format parser (traditional CIS tables and modern eCourts India JSON-LD/React timelines).
  - Session creation, status checking, and manual termination (`DELETE /api/v1/search/session/{id}`).
  - Order PDF download URL generation and metadata extraction.
  - Mock mode fallback for local development and test automation.
* **Live Query Resiliency**:
  - Browser impersonation via `curl_cffi` to prevent blockages on modern portal endpoints.
