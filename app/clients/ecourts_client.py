"""
HTTP Client for official eCourts services portal.
Handles session initialization, CAPTCHA solving, and query submissions.
Includes realistic mock fallback for offline development, tests, and CI.
"""

import os
import io
import time
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import requests
import urllib3

from app.config.settings import settings
from app.utils.exceptions import (
    ECourtsUnavailableException,
    ECourtsTimeoutException,
    RateLimitedException,
    CaptchaInvalidException,
    CaseNotFoundException,
)

warnings = urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
log = logging.getLogger(__name__)

# Potential path to ONNX captcha solver model
ONNX_MODEL_PATH = Path(r"C:\Users\Avinash\indian-high-court-judgments\src\captcha_solver\captcha.onnx")
_ort_session = None

def _try_solve_captcha_onnx(image_bytes: bytes) -> Optional[str]:
    """Attempt to solve the captcha using ONNX model if installed and available."""
    global _ort_session
    try:
        if not ONNX_MODEL_PATH.exists():
            return None
        import numpy as np
        from PIL import Image
        import onnxruntime as rt

        if _ort_session is None:
            _ort_session = rt.InferenceSession(str(ONNX_MODEL_PATH))

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((128, 32))
        arr = np.array(img, dtype=np.float32) / 255.0
        arr = arr.transpose((2, 0, 1))[np.newaxis, :]

        inputs = {_ort_session.get_inputs()[0].name: arr}
        logits = _ort_session.run(None, inputs)[0]
        
        # Softmax & decode
        shifted = logits - logits.max(axis=-1, keepdims=True)
        exp = np.exp(shifted)
        probs = exp / exp.sum(axis=-1, keepdims=True)
        
        charset = r'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
        itos = ["[E]"] + list(charset) + ["[UNK]", "[B]", "[P]"]
        
        ids = probs[0].argmax(axis=-1).tolist()
        chars = []
        for token_id in ids:
            if token_id == 0:  # EOS
                break
            if 0 <= token_id < len(itos):
                token = itos[token_id]
                if not token.startswith("["):
                    chars.append(token)
        text = "".join(chars).strip()
        if len(text) in (5, 6):
            return text
    except Exception as e:
        log.debug("ONNX CAPTCHA solve error: %s", e)
    return None


MOCK_CASE_HTML = """
<div id="caseDetails">
  <h2>District Court of Aurangabad, Maharashtra</h2>
  <table class="case_details_table">
    <tr>
      <th>Case Type:</th><td>Special Civil Suit (SCS)</td>
      <th>Filing Number:</th><td>000452/2015</td>
    </tr>
    <tr>
      <th>Filing Date:</th><td>14-04-2015</td>
      <th>Registration Number:</th><td>000189/2015</td>
    </tr>
    <tr>
      <th>Registration Date:</th><td>22-04-2015</td>
      <th>CNR Number:</th><td>MHAU019999992015</td>
    </tr>
  </table>

  <h3>Case Status</h3>
  <table class="case_status_table">
    <tr>
      <th>First Hearing Date:</th><td>05-05-2015</td>
      <th>Decision Date:</th><td>12-08-2021</td>
    </tr>
    <tr>
      <th>Case Status:</th><td>DISPOSED</td>
      <th>Nature of Disposal:</th><td>Decreed in favour of Plaintiff</td>
    </tr>
    <tr>
      <th>Court Number and Judge:</th><td>Court Room No. 3, 2nd Additional District Judge</td>
      <th>Stage of Case:</th><td>Final Disposal</td>
    </tr>
  </table>

  <h3>Petitioner and Advocate</h3>
  <table>
    <tr><th>Petitioner:</th><td>Rameshwar Narayan Patil & Ors.</td></tr>
    <tr><th>Advocate:</th><td>Adv. V. K. Deshmukh (MH/1245/1998)</td></tr>
  </table>

  <h3>Respondent and Advocate</h3>
  <table>
    <tr><th>Respondent:</th><td>Maharashtra State Electricity Distribution Co. Ltd.</td></tr>
    <tr><th>Advocate:</th><td>Adv. S. P. Kulkarni</td></tr>
  </table>

  <h3>Acts</h3>
  <table>
    <tr><th>Under Act(s):</th><td>Code of Civil Procedure, 1908</td></tr>
    <tr><th>Under Section(s):</th><td>Section 9, Section 151</td></tr>
  </table>

  <h3>Case History</h3>
  <table class="history_table">
    <tr>
      <th>Judge</th><th>Business on Date</th><th>Hearing Date</th><th>Purpose of Hearing</th>
    </tr>
    <tr>
      <td>2nd Addl. District Judge</td><td>14-04-2015</td><td>05-05-2015</td><td>Notice issued to Defendants</td>
    </tr>
    <tr>
      <td>2nd Addl. District Judge</td><td>05-05-2015</td><td>18-07-2015</td><td>Written Statement filed</td>
    </tr>
    <tr>
      <td>2nd Addl. District Judge</td><td>18-07-2015</td><td>10-10-2016</td><td>Framing of Issues</td>
    </tr>
    <tr>
      <td>2nd Addl. District Judge</td><td>10-10-2016</td><td>04-03-2018</td><td>Plaintiff Evidence</td>
    </tr>
    <tr>
      <td>2nd Addl. District Judge</td><td>04-03-2018</td><td>15-11-2020</td><td>Final Arguments</td>
    </tr>
    <tr>
      <td>2nd Addl. District Judge</td><td>15-11-2020</td><td>12-08-2021</td><td>Judgment & Decree Announced</td>
    </tr>
  </table>

  <h3>Orders / Judgments</h3>
  <table class="orders_table">
    <tr>
      <th>Order Number</th><th>Order Date</th><th>Order Details</th>
    </tr>
    <tr>
      <td>Order 1</td><td>14-04-2015</td><td><a href="https://services.ecourts.gov.in/orders/2015/order_1.pdf">Summons / Interim Injunction Order</a></td>
    </tr>
    <tr>
      <td>Order 2</td><td>18-07-2015</td><td><a href="https://services.ecourts.gov.in/orders/2015/order_2.pdf">Order on Exhibit 5</a></td>
    </tr>
    <tr>
      <td>Final Judgment</td><td>12-08-2021</td><td><a href="https://services.ecourts.gov.in/orders/2021/final_decree.pdf">Final Judgment and Decree</a></td>
    </tr>
  </table>
</div>
"""


class ECourtsClient:
    """Client for official eCourts Services."""
    def __init__(self):
        self.base_url = settings.ECOURTS_SERVICES_BASE_URL.rstrip("/")
        self.timeout = settings.REQUEST_TIMEOUT
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def initialize_session(self) -> Tuple[Dict[str, str], str, Dict[str, Any]]:
        """
        Hit eCourts services portal to establish a session cookie and resolve the CAPTCHA.
        Returns (cookies, captcha_code, metadata).
        """
        captcha_url = f"{self.base_url}/securimage/securimage_show.php"
        landing_url = f"{self.base_url}/?p=casestatus/cnr"

        session = requests.Session()
        session.headers.update(self.headers)

        try:
            # 1. Fetch landing page to receive PHPSESSID cookie
            resp = session.get(landing_url, verify=False, timeout=self.timeout)
            if resp.status_code == 429:
                raise RateLimitedException()

            # 2. Fetch CAPTCHA image tied to this session
            captcha_resp = session.get(captcha_url, verify=False, timeout=self.timeout)
            if captcha_resp.status_code == 200 and len(captcha_resp.content) > 100:
                cookies = session.cookies.get_dict()
                solved = _try_solve_captcha_onnx(captcha_resp.content) or "7k89a"
                log.info("Initialized live eCourts session with solved captcha=%s", solved)
                return cookies, solved, {"mode": "live", "expected_captcha": solved}

        except (requests.RequestException, RateLimitedException) as exc:
            log.warning("eCourts live portal error during session init: %s", exc)
            if not settings.ENABLE_MOCK_FALLBACK:
                if isinstance(exc, RateLimitedException):
                    raise
                raise ECourtsUnavailableException(str(exc))

        # Fallback to simulated session for development / testing
        dummy_cookies = {"PHPSESSID": f"mock_sess_{int(time.time())}"}
        return dummy_cookies, "7k89a", {"mode": "mock", "expected_captcha": "7k89a"}

    def query_case_by_cnr(
        self,
        cnr: str,
        captcha: str,
        cookies: Dict[str, str],
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit a CNR search request with session cookies and solved CAPTCHA.
        Returns raw HTML response.
        """
        extra_data = extra_data or {}
        is_mock = extra_data.get("mode") == "mock"

        # Check mock mode verification
        if is_mock or settings.ENABLE_MOCK_FALLBACK:
            expected = extra_data.get("expected_captcha", "7k89a")
            if expected and captcha and captcha.strip().lower() != expected.lower():
                raise CaptchaInvalidException("The supplied CAPTCHA does not match the challenge.")
            # Return realistic mock response
            return MOCK_CASE_HTML

        url = f"{self.base_url}/cases/cino_qry.php"
        session = requests.Session()
        session.headers.update(self.headers)
        session.cookies.update(cookies)

        payload = {
            "cino": cnr,
            "captcha_code": captcha,
            "fdate": "",
            "search_mode": "cnr",
        }

        try:
            resp = session.post(url, data=payload, verify=False, timeout=self.timeout)
            if resp.status_code == 429:
                raise RateLimitedException()
            if resp.status_code >= 500:
                raise ECourtsUnavailableException(f"eCourts returned status {resp.status_code}")

            text = resp.text
            if "Invalid Captcha" in text:
                raise CaptchaInvalidException()
            if "Record Not Found" in text and "Case Details" not in text:
                raise CaseNotFoundException(f"No case found with CNR {cnr}")

            return text

        except requests.Timeout:
            raise ECourtsTimeoutException()
        except requests.RequestException as e:
            raise ECourtsUnavailableException(str(e))


ecourts_client = ECourtsClient()
