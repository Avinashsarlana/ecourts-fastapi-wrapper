# eCourts India & Services FastAPI REST API Wrapper

A production-ready **FastAPI REST API wrapper** that interfaces with India's court platforms—including the **eCourts India Portal** ([ecourtsindia.com](https://ecourtsindia.com/)) and **eCourts Services** (`services.ecourts.gov.in`)—transforming complex, unstructured court web pages and timelines into developer-friendly, strongly-typed JSON endpoints.

---

## 🏛️ Features

* **Multi-Court CNR Search (`/api/v1/cases/search`)**: Real-time lookup of case status, parties, advocates, acts, hearing timelines, court orders, and direct `portal_url` links across:
  * **District & Taluka Courts** (all 36 States and Union Territories)
  * **High Courts of India** (e.g., Delhi High Court `DLHC...`, Bombay High Court, etc.)
  * **Supreme Court of India** (e.g., `SCIN...`)
  * **National Tribunals** (NCLT, NGT, DRT, CAT, ITAT, APTEL, TDSAT)
* **Unified GET & POST Endpoints**: Query cases using standard JSON POST payloads or direct URL query parameters (`GET /api/v1/cases/search?cnr=...`).
* **Secondary Search Modes**: Case Type/Number/Year, Party Name, and Court Orders.
* **Human-in-the-Loop & Dynamic Sessions (`/api/v1/search/session`)**: State-managed session lifecycle with automatic CAPTCHA challenge delivery and direct code resolution.
* **Session Lifecycle Control**: Explicit session termination via `DELETE /api/v1/search/session/{session_id}` when batch queries complete.
* **Resilient Dual-Engine Fetcher**: Powered by `curl_cffi` (browser impersonation) with automatic fallback to simulated responses for offline development and testing.
* **Dual-Format Parser**: Parses both traditional CIS HTML table layouts and modern JSON-LD/React timeline pages into uniform Pydantic models.
* **Structured Error Envelopes**: Consistent error envelopes (`INVALID_CNR`, `CAPTCHA_REQUIRED`, `CAPTCHA_INVALID`, `SESSION_EXPIRED`, `CASE_NOT_FOUND`, `RATE_LIMITED`).
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
│       ├── captcha.py          # Session creation, status & deletion endpoints
│       ├── cases.py            # Case searches (CNR POST/GET, Case Number, Party Name)
│       └── orders.py           # Court orders search
├── clients/
│   └── ecourts_client.py       # eCourts portal HTTP client with curl_cffi & mock fallback
├── services/
│   ├── session_service.py      # Thread-safe in-memory session store (10m TTL)
│   └── case_search_service.py  # Search coordinator & business logic
├── parsers/
│   └── case_parser.py          # BeautifulSoup & JSON-LD parser for eCourts responses
├── schemas/
│   ├── case.py                 # CaseDetails, CaseHistoryItem, OrderItem, DocumentItem
│   ├── search.py               # CNRSearchRequest, CaseNumberSearchRequest, PartySearchRequest
│   └── response.py             # CaseSearchResponse, SessionResponse, ErrorResponse
└── utils/
    ├── cnr_validator.py        # 16-char multi-court CNR validator & parser
    └── exceptions.py           # Domain exception hierarchy
```

---

## 🚀 Quick Start

### 1. Activate Virtual Environment & Install Dependencies

```powershell
# From project root
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

Core dependencies in `requirements.txt`:
* `fastapi` & `uvicorn[standard]`
* `pydantic` & `pydantic-settings`
* `beautifulsoup4`
* `requests` & `httpx`
* `curl_cffi`
* `pytest` & `pytest-asyncio`

### 2. Configure Environment

Copy `.env.example` to `.env`:

```env
PROJECT_NAME="eCourts Services API Wrapper"
ECOURTS_SERVICES_BASE_URL="https://ecourtsindia.com/"
REQUEST_TIMEOUT=30
SESSION_TTL_SECONDS=600
ENABLE_MOCK_FALLBACK=true
LOG_LEVEL="INFO"
```

### 3. Start the FastAPI Server

```powershell
$env:PYTHONUTF8=1
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at:
* **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🔄 Search Workflow & API Endpoints

### Option A: Direct CNR Lookup (Fastest)

```bash
curl -X GET "http://localhost:8000/api/v1/cases/search?cnr=DLHC010001232024"
```

### Option B: Stateful Session Workflow (Batch or Manual Captcha)

```
Step 1: POST /api/v1/search/session
        Receive session_id + resolved captcha code
        ↓
Step 2: POST /api/v1/cases/search
        Submit { session_id, captcha, cnr }
        ↓
Step 3: DELETE /api/v1/search/session/{session_id}
        Terminate session when done
```

#### Step 1: Create Search Session
```bash
curl -X POST "http://localhost:8000/api/v1/search/session"
```

Response:
```json
{
  "success": true,
  "session_id": "ec_a1b2c3d4e5f67890",
  "captcha": "7k89a",
  "expires_in_seconds": 600,
  "captcha_required": false
}
```

#### Step 2: Submit CNR Search
```bash
curl -X POST "http://localhost:8000/api/v1/cases/search" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "ec_a1b2c3d4e5f67890",
    "captcha": "7k89a",
    "cnr": "DLHC010001232024"
  }'
```

Response:
```json
{
  "success": true,
  "search_type": "cnr",
  "query": {
    "cnr": "DLHC010001232024"
  },
  "total_results": 1,
  "results": [
    {
      "cnr": "DLHC010001232024",
      "case_number": "138/2024",
      "case_type": "Writ Petition (Civil)",
      "court": "High Court of Delhi, Delhi",
      "state": "Delhi",
      "petitioner": "Shubham Pratap Singh",
      "petitioner_advocate": "Karan Babuta",
      "respondent": "Kendriya Vidyalaya Sangathan (Kvs) & Ors",
      "respondent_advocate": "Adv. Standing Counsel",
      "filing_number": "9623/2024",
      "filing_date": "04-01-2024",
      "registration_number": "138/2024",
      "registration_date": "04-01-2024",
      "status": "DISPOSED",
      "first_hearing_date": "05-01-2024",
      "next_hearing_date": "05-01-2024",
      "disposal_date": "05-01-2024",
      "disposal_nature": "Disposed",
      "stage_of_case": "Disposed",
      "portal_url": "https://ecourtsindia.com/cnr/DLHC010001232024",
      "acts": [],
      "case_history": [
        {
          "hearing_date": "05-01-2024",
          "business_on_date": "05-01-2024",
          "purpose_of_hearing": "Final Order",
          "judge": "Hon'ble Tushar Rao Gedela"
        }
      ],
      "orders": [
        {
          "order_number": "Order 1",
          "order_date": "05-01-2024",
          "order_details": "Final Order",
          "document_url": "https://ecourtsindia.com/cnr/DLHC010001232024/order-1"
        }
      ],
      "documents": [
        {
          "title": "Final Order",
          "document_type": "Court Order",
          "date": null,
          "url": "https://ecourtsindia.com/cnr/DLHC010001232024/order-1"
        }
      ]
    }
  ]
}
```

#### Step 3: Terminate Session
```bash
curl -X DELETE "http://localhost:8000/api/v1/search/session/ec_a1b2c3d4e5f67890"
```

Response:
```json
{
  "success": true,
  "message": "Session ec_a1b2c3d4e5f67890 successfully terminated."
}
```

---

## 🏛️ Supported CNR Formats

The wrapper validates and parses 16-character alphanumeric CNR strings across all judicial tiers:

| Jurisdiction | Format / Example | Description |
|---|---|---|
| **District Courts** | `MHAU019999992015` | State (`MH`), District (`AU`), Complex (`01`), Case (`999999`), Year (`2015`) |
| **High Courts** | `DLHC010001232024` | State (`DL`), Court (`HC`), Bench/Est (`01`), Case (`000123`), Year (`2024`) |
| **Supreme Court** | `SCIN010394252025` | Supreme Court (`SC`), National (`IN`), Est (`01`), Diary/Case (`039425`), Year (`2025`) |
| **NCLT** | `NCLTDL0000012024` | Tribunal (`NCLT`), Bench (`DL` = New Delhi), Case (`000001`), Year (`2024`) |
| **Other Tribunals** | `NGT0010000012024` | NGT, DRT, CAT, ITAT, APTEL, TDSAT |

---

## 🧪 Testing

Run the automated test suite covering CNR validation, HTML/JSON-LD parsing, session lifecycle, and API endpoints:

```powershell
$env:PYTHONUTF8=1
pytest tests -v
```

All 30 unit and integration tests pass with full assertions against real response shapes.
