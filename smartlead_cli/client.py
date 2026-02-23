"""HTTP client wrapper for Smartlead API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import httpx
import typer

from smartlead_cli.output import print_error
from smartlead_cli.serialize import to_data

if TYPE_CHECKING:
    from smartlead_cli.config import Config


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class ResponseEnvelope:
    status_code: int
    headers: dict[str, str]
    data: Any


@dataclass
class SmartleadClient:
    cfg: "Config"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> ResponseEnvelope:
        if require_auth and not self.cfg.api_key:
            print_error(
                "auth_error",
                "No Smartlead API key configured. Set SMARTLEAD_API_KEY, use --api-key, or run `smartlead config init`.",
            )
            raise typer.Exit(1)

        merged_params: dict[str, Any] = {}
        if params:
            merged_params.update({k: v for k, v in params.items() if v is not None})
        if require_auth and self.cfg.api_key:
            merged_params.setdefault("api_key", self.cfg.api_key)

        url = _resolve_url(self.cfg.base_url, path)
        max_attempts = max(1, int(self.cfg.retries))

        for attempt in range(max_attempts):
            try:
                with httpx.Client(timeout=self.cfg.timeout_seconds) as client:
                    resp = client.request(method.upper(), url, params=merged_params, json=json_body, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt < max_attempts - 1:
                    time.sleep(min(2**attempt, 5))
                    continue
                print_error("timeout", f"Request timed out after {self.cfg.timeout_seconds}s", detail=str(exc))
                raise typer.Exit(1)
            except httpx.HTTPError as exc:
                print_error("network_error", f"Network error: {exc}")
                raise typer.Exit(1)

            if resp.status_code in RETRYABLE_STATUS_CODES and attempt < max_attempts - 1:
                delay = _retry_after_seconds(resp) or min(2**attempt, 5)
                time.sleep(delay)
                continue

            if resp.status_code >= 400:
                _handle_error_response(resp)
                raise typer.Exit(1)

            return ResponseEnvelope(status_code=resp.status_code, headers=dict(resp.headers), data=_parse_response(resp))

        print_error("cli_error", "Unexpected request failure")
        raise typer.Exit(1)


def get_client(cfg: "Config") -> SmartleadClient:
    return SmartleadClient(cfg)


def api_request(
    cfg: "Config",
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    require_auth: bool = True,
    include_meta: bool = False,
) -> Any:
    result = get_client(cfg).request(
        method,
        path,
        params=params,
        json_body=json_body,
        headers=headers,
        require_auth=require_auth,
    )
    if include_meta:
        return {
            "status_code": result.status_code,
            "headers": result.headers,
            "data": to_data(result.data),
        }
    return result.data


def _resolve_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = base_url.rstrip("/") + "/"
    rel = path.lstrip("/")
    if rel.startswith("api/v1/"):
        rel = rel[len("api/v1/") :]
    return urljoin(base, rel)


def _retry_after_seconds(resp: httpx.Response) -> int | None:
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(1, int(value))
    except ValueError:
        return None


def _parse_response(resp: httpx.Response) -> Any:
    content_type = (resp.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            return resp.json()
        except Exception:
            return {"text": resp.text}
    if not resp.content:
        return {"ok": True, "status_code": resp.status_code}
    try:
        text = resp.text
        return {"text": text}
    except UnicodeDecodeError:
        return resp.content


def _handle_error_response(resp: httpx.Response) -> None:
    detail: Any = None
    message = f"Smartlead API request failed ({resp.status_code})"
    try:
        detail = resp.json()
        if isinstance(detail, dict):
            message = str(detail.get("message") or detail.get("error") or message)
    except Exception:
        detail = resp.text[:1000] if resp.text else None

    status = resp.status_code
    if status == 401:
        print_error("auth_error", "Authentication failed. Check SMARTLEAD_API_KEY.", status_code=status, detail=detail)
    elif status == 403:
        print_error("forbidden", "Permission denied.", status_code=status, detail=detail)
    elif status == 404:
        print_error("not_found", "Resource not found.", status_code=status, detail=detail)
    elif status == 429:
        print_error("rate_limit", "Rate limit exceeded.", status_code=status, detail=detail)
    elif status == 400:
        print_error("validation_error", message, status_code=status, detail=detail)
    else:
        print_error("api_error", message, status_code=status, detail=detail)
