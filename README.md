# FastAPI Wrapper for official eCourts Services

A production-ready **FastAPI REST API wrapper** that interfaces with India's official **eCourts Services** (`services.ecourts.gov.in`), transforming complex, unstructured court web pages into developer-friendly, strongly-typed JSON endpoints.

---

## 🏛️ Features

* **Primary CNR Search (`/api/v1/cases/search`)**: Real-time lookup of case status, parties, advocates, acts, hearing timelines, and order documents via 16-character alphanumeric CNR.
* **Secondary Search Modes**: Case Number, Party Name, and Court Orders.
* **Human-in-the-Loop CAPTCHA Workflow**: State-managed session lifecycle (`/api/v1/search/session`) that surfaces official government CAPTCHA challenges to clients as Base64 data URIs without violating anti-bot policies.
* **Clean Layered Architecture**: Clear separation of API routes, client communication, parsers, domain services, Pydantic v2 schemas, and exception handling.
* **Structured Error Envelopes**: Standard error codes (`INVALID_CNR`, `CAPTCHA_REQUIRED`, `CAPTCHA_INVALID`, `SESSION_EXPIRED`, `CASE_NOT_FOUND`, `RATE_LIMITED`).
* **Offline Mock & Test Mode**: Built-in test fixtures and realistic mock fallback for reliable CI/CD and offline development.
* **Interactive Documentation**: Auto-generated Swagger (`/docs`) and ReDoc (`/redoc`).

---

## 🏗️ Architecture

```
app/
├── main.py                     # FastAPI application setup, middleware, exception handlers
├── config/
│   └── settings.py             # Pydantic BaseSettings loaded from .env
├── api/
│   └── routes/
│       ├── captcha.py          # Session creation & CAPTCHA challenge delivery
│       ├── cases.py            # Case searches (CNR, Case Number, Party Name)
│       └── orders.py           # Court orders search
├── clients/
│   └── ecourts_client.py       # eCourts portal HTTP client with mock fallback
├── services/
│   ├── session_service.py      # Thread-safe in-memory session store (10m TTL)
│   └── case_search_service.py  # Search coordinator & business logic
├── parsers/
│   └── case_parser.py          # BeautifulSoup parser for eCourts HTML tables
├── schemas/
│   ├── case.py                 # CaseDetails, CaseHistoryItem, OrderItem
│   ├── search.py               # CNRSearchRequest, PartySearchRequest
│   └── response.py             # CaseSearchResponse, SessionResponse, ErrorResponse
└── utils/
    ├── cnr_validator.py        # 16-char CNR validation & state parser
    └── exceptions.py           # Domain exception hierarchy
```

---

## 🚀 Quick Start

### 1. Activate Virtual Environment & Install Dependencies

```powershell
# From project root
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install fastapi uvicorn[standard] pydantic pydantic-settings beautifulsoup4 requests pytest
```

### 2. Start the FastAPI Server

```powershell
$env:PYTHONUTF8=1
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at:
* **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🔄 The Human-in-the-Loop CAPTCHA Workflow

Because the official eCourts platform enforces image CAPTCHAs, searches follow a 2-step session flow:

```
Step 1: POST /api/v1/search/session
        Receive session_id + CAPTCHA challenge (Base64 data URI)
        ↓
Step 2: User solves CAPTCHA
        ↓
Step 3: POST /api/v1/cases/search
        Submit { session_id, captcha, cnr }
        ↓
Receive Normalized JSON Case Details
```

### Example via cURL

#### Step 1: Create Search Session
```bash
curl -X POST "http://localhost:8000/api/v1/search/session"
```

Response:
```json
{
  "success": true,
  "session_id": "ec_a1b2c3d4e5f67890",
  "captcha_required": true,
  "captcha_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK...",
  "audio_url": null,
  "expires_in_seconds": 600
}
```

#### Step 2: Submit CNR Search with Solved CAPTCHA
```bash
curl -X POST "http://localhost:8000/api/v1/cases/search" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "ec_a1b2c3d4e5f67890",
    "captcha": "7k89a",
    "cnr": "MHAU019999992015"
  }'
```

Response:
```json
{
  "success": true,
  "search_type": "cnr",
  "query": {
    "cnr": "MHAU019999992015"
  },
  "total_results": 1,
  "results": [
    {
      "cnr": "MHAU019999992015",
      "case_number": "000189/2015",
      "case_type": "Special Civil Suit (SCS)",
      "court": "District Court of Aurangabad, Maharashtra",
      "state": "Maharashtra",
      "petitioner": "Rameshwar Narayan Patil & Ors.",
      "petitioner_advocate": "Adv. V. K. Deshmukh (MH/1245/1998)",
      "respondent": "Maharashtra State Electricity Distribution Co. Ltd.",
      "respondent_advocate": "Adv. S. P. Kulkarni",
      "filing_number": "000452/2015",
      "filing_date": "14-04-2015",
      "registration_number": "000189/2015",
      "registration_date": "22-04-2015",
      "status": "DISPOSED",
      "first_hearing_date": "05-05-2015",
      "next_hearing_date": "12-08-2021",
      "disposal_date": null,
      "disposal_nature": "Decreed in favour of Plaintiff",
      "stage_of_case": "Final Disposal",
      "acts": [
        {
          "act": "Code of Civil Procedure, 1908",
          "section": "Section 9, Section 151"
        }
      ],
      "case_history": [
        {
          "hearing_date": "05-05-2015",
          "business_on_date": "14-04-2015",
          "purpose_of_hearing": "Notice issued to Defendants",
          "judge": "2nd Addl. District Judge"
        },
        {
          "hearing_date": "12-08-2021",
          "business_on_date": "15-11-2020",
          "purpose_of_hearing": "Judgment & Decree Announced",
          "judge": "2nd Addl. District Judge"
        }
      ],
      "orders": [
        {
          "order_number": "Order 1",
          "order_date": "14-04-2015",
          "order_details": "Summons / Interim Injunction Order",
          "document_url": "https://services.ecourts.gov.in/orders/2015/order_1.pdf"
        }
      ],
      "documents": [
        {
          "title": "Order Order 1 (14-04-2015)",
          "document_type": "Court Order PDF",
          "date": "14-04-2015",
          "url": "https://services.ecourts.gov.in/orders/2015/order_1.pdf"
        }
      ]
    }
  ]
}
```

---

## 🧪 Testing

Run the automated test suite covering CNR validation, HTML table parsing, and API endpoints:

```powershell
$env:PYTHONUTF8=1
.\.venv\Scripts\pytest.exe tests -v
```

All 18 tests pass with full assertions against real response shapes.
