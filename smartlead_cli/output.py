"""Output helpers: JSON, structured errors, and optional Rich tables."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Optional

from rich import box
from rich.console import Console
from rich.table import Table

err_console = Console(stderr=True)
out_console = Console()

TableBuilder = Callable[[Any], Optional[Table]]


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False))


def print_error(
    error_type: str,
    message: str,
    status_code: int | None = None,
    detail: Any | None = None,
) -> None:
    payload: dict[str, Any] = {"type": error_type, "message": message}
    if status_code is not None:
        payload["status_code"] = status_code
    if detail is not None:
        payload["detail"] = detail
    err_console.print_json(json.dumps({"error": payload}, ensure_ascii=False))


def emit(data: Any, pretty: bool = False, table_builder: TableBuilder | None = None) -> None:
    if pretty:
        table = table_builder(data) if table_builder else None
        if table is not None:
            out_console.print(table)
            return
        out_console.print_json(json.dumps(data, ensure_ascii=False))
        return
    print_json(data)


def read_text_arg(value: str) -> str:
    if value == "-":
        if sys.stdin.isatty():
            err_console.print("[dim]Reading from stdin (Ctrl+D to finish):[/dim]")
        return sys.stdin.read()
    return value


def simple_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], title: str | None = None) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    for header, _ in columns:
        table.add_column(header)
    for row in rows:
        table.add_row(*[_cell(_resolve(row, key)) for _, key in columns])
    return table


def campaigns_table(data: Any) -> Table | None:
    rows = _as_list(data)
    if rows is None:
        return None
    display = []
    for item in rows[:200]:
        if not isinstance(item, dict):
            continue
        display.append(
            {
                "id": item.get("id") or item.get("campaign_id"),
                "name": item.get("name"),
                "status": item.get("status"),
                "client": item.get("client_id"),
                "created": item.get("created_at") or item.get("createdAt"),
            }
        )
    if not display:
        return None
    return simple_table(
        display,
        [("ID", "id"), ("Name", "name"), ("Status", "status"), ("Client", "client"), ("Created", "created")],
        title="Campaigns",
    )


def campaign_leads_table(data: Any) -> Table | None:
    rows = _as_list(data)
    if rows is None:
        return None
    display = []
    for item in rows[:200]:
        if not isinstance(item, dict):
            continue
        display.append(
            {
                "id": item.get("id") or item.get("lead_id"),
                "email": item.get("email") or _resolve(item, "lead.email"),
                "name": item.get("name") or item.get("first_name"),
                "status": item.get("status") or item.get("lead_status"),
                "sequence": item.get("email_sequence_number"),
            }
        )
    if not display:
        return None
    return simple_table(
        display,
        [("Lead ID", "id"), ("Email", "email"), ("Name", "name"), ("Status", "status"), ("Seq", "sequence")],
        title="Campaign Leads",
    )


def webhooks_table(data: Any) -> Table | None:
    rows = _as_list(data)
    if rows is None:
        return None
    display = []
    for item in rows[:200]:
        if not isinstance(item, dict):
            continue
        display.append(
            {
                "id": item.get("id") or item.get("webhook_id"),
                "url": item.get("url") or item.get("webhook_url"),
                "event": item.get("event") or item.get("event_type"),
                "active": item.get("is_active") if "is_active" in item else item.get("active"),
            }
        )
    if not display:
        return None
    return simple_table(display, [("ID", "id"), ("URL", "url"), ("Event", "event"), ("Active", "active")], title="Webhooks")


def statistics_table(data: Any) -> Table | None:
    rows = _as_list(data)
    if rows is None:
        return None
    keys = ["lead_id", "email", "status", "email_sequence_number", "open_count", "click_count", "reply_count"]
    first = next((r for r in rows if isinstance(r, dict)), None)
    if first is None:
        return None
    cols = [(k, k) for k in keys if any(isinstance(r, dict) and k in r for r in rows[:25])]
    if not cols:
        cols = [(k, k) for k in list(first.keys())[:6]]
    return simple_table([r for r in rows[:200] if isinstance(r, dict)], cols, title="Campaign Statistics")


def _as_list(data: Any) -> list[Any] | None:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "results", "items", "campaigns", "leads", "webhooks"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return None


def _resolve(data: Any, dotted: str) -> Any:
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text if len(text) <= 90 else text[:87] + "..."
