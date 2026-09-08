"""
ABA Pay (KHQRcc) gateway helpers.

Endpoints documented at https://khqr.cc
  - Direct QR API:      POST /api/<profile>/payment-gateway/v1/payments/qr-api-khqrcc
  - Verify / Check V2:  POST /api/<profile>/payment-gateway/v1/payments/check-transv2-khqrcc
"""
import hashlib
import os

import requests

GATEWAY_BASE = os.getenv("KHQRCC_GATEWAY_URL", "https://khqr.cc").rstrip("/")


def _profile_id() -> str:
    return (os.getenv("KHQRCC_PROFILE_ID") or "").strip()


def _secret_key() -> str:
    return (os.getenv("KHQRCC_SECRET_KEY") or "").strip()


def is_configured() -> bool:
    """True when the merchant profile + secret are present in the environment."""
    return bool(_profile_id() and _secret_key())


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _post(path: str, data: dict) -> dict:
    url = f"{GATEWAY_BASE}/api/{_profile_id()}/{path}"
    try:
        resp = requests.post(url, data=data, timeout=30)
    except requests.RequestException as exc:
        return {"responseCode": 1, "responseMessage": f"Gateway unreachable: {exc}"}
    try:
        return resp.json()
    except ValueError:
        return {"responseCode": 1, "responseMessage": f"Gateway HTTP {resp.status_code}"}


def create_qr_payment(*, transaction_id: str, amount: float, success_url: str,
                      remark: str, items: str = "") -> dict:
    """
    Direct QR API - returns the raw KHQR + PNG URL so the storefront can render
    the QR code in-page and let the customer scan it with ABA Mobile.
    """
    if not is_configured():
        raise RuntimeError("KHQRCC_PROFILE_ID / KHQRCC_SECRET_KEY are not configured")
    amount_str = f"{amount:.2f}"
    # hash = sha1(secret + transaction_id + amount + success_url + remark)
    payment_hash = _sha1(f"{_secret_key()}{transaction_id}{amount_str}{success_url}{remark}")

    payload = {
        "transaction_id": transaction_id,
        "amount": amount_str,
        "success_url": success_url,
        "remark": remark,
        "hash": payment_hash,
    }
    if items:
        payload["items"] = items

    result = _post("payment-gateway/v1/payments/qr-api-khqrcc", payload)
    if result.get("responseCode") != 0:
        raise RuntimeError(result.get("responseMessage") or "KHQRcc QR creation failed")

    data = result.get("data") or {}
    qr_url = data.get("qr_url") or ""
    if qr_url and not qr_url.startswith(("http://", "https://")):
        qr_url = f"{GATEWAY_BASE}{qr_url}"
    return {
        "transaction_id": data.get("transaction_id") or transaction_id,
        "amount": amount_str,
        "qr_url": qr_url,
        "qr": data.get("qr", ""),
        "raw": result,
    }


def check_payment(transaction_id: str) -> dict:
    """
    Poll Check V2. Returns one of:
      {"status": "success", "amount": ...}
      {"status": "pending", ...}
      {"status": "error", "message": ...}
    """
    payment_hash = _sha1(f"{_secret_key()}{transaction_id}")
    result = _post(
        "payment-gateway/v1/payments/check-transv2-khqrcc",
        {"transaction_id": transaction_id, "hash": payment_hash},
    )
    if result.get("responseCode") != 0:
        return {
            "status": "error",
            "message": result.get("responseMessage") or "Payment verification failed",
            "raw": result,
        }
    data = result.get("data") or {}
    status = (data.get("status") or "pending").lower()
    if status in ("paid", "success"):
        status = "success"
    return {"status": status, "amount": data.get("amount"), "raw": result}
