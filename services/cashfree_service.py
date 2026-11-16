"""Cashfree Payment Gateway client for NOVEXA premium subscriptions."""

import base64
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

import aiohttp

from config import CASHFREE_APP_ID, CASHFREE_SECRET_KEY, CASHFREE_ENV, CASHFREE_API_VERSION

logger = logging.getLogger("novexa.cashfree")

PRODUCTION_BASE = "https://api.cashfree.com/pg"
SANDBOX_BASE = "https://sandbox.cashfree.com/pg"


class CashfreeError(Exception):
    def __init__(self, message: str, status: int = 0, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


class CashfreeService:
    def __init__(self) -> None:
        self.app_id = (CASHFREE_APP_ID or "").strip()
        self.secret_key = (CASHFREE_SECRET_KEY or "").strip()
        self.mode = "sandbox" if (CASHFREE_ENV or "").strip().lower() in {"sandbox", "test"} else "production"
        self.api_version = CASHFREE_API_VERSION or "2023-08-01"

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.secret_key)

    @property
    def base_url(self) -> str:
        return SANDBOX_BASE if self.mode == "sandbox" else PRODUCTION_BASE

    def _headers(self) -> Dict[str, str]:
        return {
            "x-client-id": self.app_id,
            "x-client-secret": self.secret_key,
            "x-api-version": self.api_version,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.configured:
            raise CashfreeError("Cashfree credentials are not configured.", status=503)
        url = f"{self.base_url}{path}"
        timeout = aiohttp.ClientTimeout(total=20)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=self._headers(), json=json_body) as resp:
                    text = await resp.text()
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        data = {"raw": text}
                    if resp.status >= 400:
                        message = ""
                        if isinstance(data, dict):
                            message = data.get("message") or data.get("error_description") or data.get("raw") or ""
                        raise CashfreeError(f"Cashfree {method} {path} failed ({resp.status}): {message}", resp.status, data if isinstance(data, dict) else {})
                    return data if isinstance(data, dict) else {"raw": data}
        except aiohttp.ClientError as exc:
            raise CashfreeError(f"Cashfree network error: {exc}") from exc

    async def create_order(
        self,
        order_id: str,
        amount: float,
        customer_id: str,
        customer_email: str,
        customer_phone: str,
        customer_name: str,
        return_url: str,
        notify_url: str,
        note: str = "",
    ) -> Dict[str, Any]:
        body = {
            "order_id": order_id,
            "order_amount": round(float(amount), 2),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": customer_id,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_name": customer_name,
            },
            "order_meta": {
                "return_url": return_url,
                "notify_url": notify_url,
            },
            "order_note": note[:200],
        }
        return await self._request("POST", "/orders", body)

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/orders/{order_id}")

    def verify_webhook_signature(self, timestamp: str, raw_body: bytes, signature: str) -> bool:
        if not (self.secret_key and timestamp and signature):
            return False
        try:
            body_text = raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray)) else str(raw_body)
        except UnicodeDecodeError:
            return False
        computed = base64.b64encode(
            hmac.new(self.secret_key.encode("utf-8"), (timestamp + body_text).encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        return hmac.compare_digest(computed, signature)


cashfree_service = CashfreeService()
