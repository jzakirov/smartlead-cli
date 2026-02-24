"""campaigns subcommand (campaigns, analytics, and campaign leads)."""

from typing import Any

import typer

from smartlead_cli.args import load_json_input, maybe_load_json_input
from smartlead_cli.client import api_request
from smartlead_cli.confirm import require_yes_or_confirm
from smartlead_cli.config import Config
from smartlead_cli.output import (
    campaign_leads_table,
    campaigns_table,
    emit,
    print_error,
    statistics_table,
)
from smartlead_cli.schemas import (
    CampaignCreateBodyModel,
    CampaignLeadUpdateBodyModel,
    CampaignLeadsAddBodyModel,
    CampaignScheduleBodyModel,
    CampaignUpdateBodyModel,
)

app = typer.Typer(name="campaigns", help="Smartlead campaign operations.", no_args_is_help=True)
analytics_app = typer.Typer(
    name="analytics", help="Campaign analytics helpers.", no_args_is_help=True
)
leads_app = typer.Typer(name="leads", help="Campaign lead operations.", no_args_is_help=True)

app.add_typer(analytics_app, name="analytics")
app.add_typer(leads_app, name="leads")

LEAD_UPDATE_BODY_KEYS = tuple(CampaignLeadUpdateBodyModel.model_fields.keys())


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _campaign_lead_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        rows = data.get("data")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _lead_entry_matches_id(row: dict[str, Any], lead_id: int) -> bool:
    nested_lead = row.get("lead")
    candidates = [
        row.get("lead_id"),
        row.get("id"),
        nested_lead.get("id") if isinstance(nested_lead, dict) else None,
    ]
    return any(_coerce_int(v) == lead_id for v in candidates)


def _find_campaign_lead_entry(
    cfg: Config,
    campaign_id: int,
    lead_id: int,
    *,
    page_size: int = 100,
    max_pages: int = 20,
) -> dict[str, Any] | None:
    offset = 0
    for _ in range(max_pages):
        payload = api_request(
            cfg,
            "GET",
            f"/campaigns/{campaign_id}/leads",
            params={"offset": offset, "limit": page_size},
        )
        rows = _campaign_lead_rows(payload)
        for row in rows:
            if _lead_entry_matches_id(row, lead_id):
                return row
        if len(rows) < page_size:
            return None
        offset += page_size
    return None


def _extract_patchable_lead_input(entry: dict[str, Any]) -> dict[str, Any]:
    nested = entry.get("lead") if isinstance(entry.get("lead"), dict) else {}
    source = nested if isinstance(nested, dict) else {}
    body: dict[str, Any] = {}
    for key in LEAD_UPDATE_BODY_KEYS:
        if key in source:
            body[key] = source[key]
    return body


@app.command("list")
def campaigns_list(
    ctx: typer.Context,
    offset: int | None = typer.Option(None, "--offset", help="Pagination offset"),
    client_id: int | None = typer.Option(None, "--client-id", help="Filter campaigns by client ID"),
    include_tags: bool | None = typer.Option(
        None,
        "--include-tags/--no-include-tags",
        help="Include tags in campaign list response",
    ),
) -> None:
    cfg: Config = ctx.obj
    params = {"offset": offset, "client_id": client_id, "include_tags": include_tags}
    data = api_request(cfg, "GET", "/campaigns", params=params)
    emit(data, pretty=cfg.pretty, table_builder=campaigns_table)


@app.command("get")
def campaigns_get(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "GET", f"/campaigns/{campaign_id}")
    emit(data, pretty=cfg.pretty)


@app.command("create")
def campaigns_create(
    ctx: typer.Context,
    name: str | None = typer.Option(
        None, "--name", help="Campaign name (required unless body provided)"
    ),
    client_id: int | None = typer.Option(None, "--client-id", help="Client ID (optional)"),
    body_json: str | None = typer.Option(
        None, "--body-json", help="Raw request JSON or '-' for stdin"
    ),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Path to JSON request body or '-' for stdin"
    ),
) -> None:
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json, body_file) if (body_json or body_file) else None
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)

    if body is None:
        if not name:
            print_error(
                "validation_error", "Provide --name or a request body via --body-json/--body-file"
            )
            raise typer.Exit(1)
        body = {"name": name}
        if client_id is not None:
            body["client_id"] = client_id

    try:
        CampaignCreateBodyModel.model_validate(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)

    data = api_request(cfg, "POST", "/campaigns/create", json_body=body)
    emit(data, pretty=cfg.pretty)


@app.command("update")
def campaigns_update(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    name: str | None = typer.Option(None, "--name", help="Campaign name"),
    client_id: int | None = typer.Option(None, "--client-id", help="Client ID (set null via body)"),
    stop_lead_settings: str | None = typer.Option(
        None, "--stop-lead-settings", help="e.g. REPLY_TO_AN_EMAIL"
    ),
    unsubscribe_text: str | None = typer.Option(None, "--unsubscribe-text", help="Custom text"),
    follow_up_percentage: int | None = typer.Option(
        None, "--follow-up-percentage", min=0, max=100, help="0..100"
    ),
    send_as_plain_text: bool | None = typer.Option(
        None, "--send-as-plain-text/--no-send-as-plain-text", help="Send emails as plain text"
    ),
    force_plain_text: bool | None = typer.Option(
        None, "--force-plain-text/--no-force-plain-text", help="Force plain text"
    ),
    enable_ai_esp_matching: bool | None = typer.Option(
        None,
        "--enable-ai-esp-matching/--no-enable-ai-esp-matching",
        help="Enable AI ESP matching",
    ),
    auto_pause_domain_leads_on_reply: bool | None = typer.Option(
        None,
        "--auto-pause-domain-leads-on-reply/--no-auto-pause-domain-leads-on-reply",
        help="Pause same-domain leads when one replies",
    ),
    ignore_ss_mailbox_sending_limit: bool | None = typer.Option(
        None,
        "--ignore-ss-mailbox-sending-limit/--no-ignore-ss-mailbox-sending-limit",
        help="Ignore shared mailbox sending limit",
    ),
    domain_level_rate_limit: bool | None = typer.Option(
        None,
        "--domain-level-rate-limit/--no-domain-level-rate-limit",
        help="Enable domain-level rate limits",
    ),
    bounce_autopause_threshold: str | None = typer.Option(
        None, "--bounce-autopause-threshold", help="Bounce threshold value"
    ),
    track_setting: list[str] = typer.Option(
        [],
        "--track-setting",
        help="Repeatable track_settings entry (e.g. DONT_TRACK_EMAIL_OPEN)",
    ),
    ai_category_id: list[int] = typer.Option(
        [],
        "--ai-category-id",
        help="Repeatable AI categorization option id",
    ),
    body_json: str | None = typer.Option(
        None, "--body-json", help="Raw request JSON or '-' for stdin"
    ),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Path to JSON request body or '-' for stdin"
    ),
) -> None:
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json, body_file) if (body_json or body_file) else None
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)

    if body is None:
        body = {}
        if name is not None:
            body["name"] = name
        if client_id is not None:
            body["client_id"] = client_id
        if stop_lead_settings is not None:
            body["stop_lead_settings"] = stop_lead_settings
        if unsubscribe_text is not None:
            body["unsubscribe_text"] = unsubscribe_text
        if follow_up_percentage is not None:
            body["follow_up_percentage"] = follow_up_percentage
        if send_as_plain_text is not None:
            body["send_as_plain_text"] = send_as_plain_text
        if force_plain_text is not None:
            body["force_plain_text"] = force_plain_text
        if enable_ai_esp_matching is not None:
            body["enable_ai_esp_matching"] = enable_ai_esp_matching
        if auto_pause_domain_leads_on_reply is not None:
            body["auto_pause_domain_leads_on_reply"] = auto_pause_domain_leads_on_reply
        if ignore_ss_mailbox_sending_limit is not None:
            body["ignore_ss_mailbox_sending_limit"] = ignore_ss_mailbox_sending_limit
        if domain_level_rate_limit is not None:
            body["domain_level_rate_limit"] = domain_level_rate_limit
        if bounce_autopause_threshold is not None:
            body["bounce_autopause_threshold"] = bounce_autopause_threshold
        if track_setting:
            body["track_settings"] = track_setting
        if ai_category_id:
            body["ai_categorisation_options"] = ai_category_id

        if not body:
            print_error(
                "validation_error",
                "Provide at least one update flag or a request body via --body-json/--body-file",
            )
            raise typer.Exit(1)

    try:
        CampaignUpdateBodyModel.model_validate(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)

    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/settings", json_body=body)
    emit(data, pretty=cfg.pretty)


@app.command("schedule")
def campaigns_schedule_update(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    timezone: str | None = typer.Option(None, "--timezone", help="IANA timezone"),
    day: list[int] = typer.Option(
        [], "--day", min=0, max=6, help="Repeatable day of week (0=Sun .. 6=Sat)"
    ),
    start_hour: str | None = typer.Option(None, "--start-hour", help="HH:MM"),
    end_hour: str | None = typer.Option(None, "--end-hour", help="HH:MM"),
    min_time_btw_emails: int | None = typer.Option(
        None, "--min-time-btw-emails", min=0, help="Minutes between emails"
    ),
    max_new_leads_per_day: int | None = typer.Option(
        None, "--max-new-leads-per-day", min=0, help="Max new leads per day"
    ),
    schedule_start_time: str | None = typer.Option(
        None, "--schedule-start-time", help="ISO datetime"
    ),
    body_json: str | None = typer.Option(
        None, "--body-json", help="Raw request JSON or '-' for stdin"
    ),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Path to JSON request body or '-' for stdin"
    ),
) -> None:
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json, body_file) if (body_json or body_file) else None
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)

    if body is None:
        body = {}
        if timezone is not None:
            body["timezone"] = timezone
        if day:
            body["days_of_the_week"] = day
        if start_hour is not None:
            body["start_hour"] = start_hour
        if end_hour is not None:
            body["end_hour"] = end_hour
        if min_time_btw_emails is not None:
            body["min_time_btw_emails"] = min_time_btw_emails
        if max_new_leads_per_day is not None:
            body["max_new_leads_per_day"] = max_new_leads_per_day
        if schedule_start_time is not None:
            body["schedule_start_time"] = schedule_start_time

        if not body:
            print_error(
                "validation_error",
                "Provide at least one schedule flag or a request body via --body-json/--body-file",
            )
            raise typer.Exit(1)

    try:
        CampaignScheduleBodyModel.model_validate(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)

    # Smartlead docs call this \"Update Campaign Schedule\" on POST /campaigns/{campaign_id}
    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}", json_body=body)
    emit(data, pretty=cfg.pretty)


@app.command("delete")
def campaigns_delete(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    require_yes_or_confirm(yes, f"Delete campaign {campaign_id}?")
    cfg: Config = ctx.obj
    data = api_request(cfg, "DELETE", f"/campaigns/{campaign_id}")
    emit(data, pretty=cfg.pretty)


@app.command("status")
def campaigns_status(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    status: str = typer.Option(..., "--status", help="Campaign status: START, PAUSED, STOPPED"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(
        cfg, "POST", f"/campaigns/{campaign_id}/status", json_body={"status": status}
    )
    emit(data, pretty=cfg.pretty)


@app.command("statistics")
def campaigns_statistics(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    offset: int | None = typer.Option(None, "--offset", help="Pagination offset"),
    limit: int | None = typer.Option(None, "--limit", help="Pagination limit (defaults to config)"),
    email_sequence_number: int | None = typer.Option(
        None, "--email-sequence-number", help="Sequence step filter"
    ),
    email_status: str | None = typer.Option(None, "--email-status", help="Email status filter"),
) -> None:
    cfg: Config = ctx.obj
    params = {
        "offset": offset,
        "limit": limit if limit is not None else cfg.default_limit,
        "email_sequence_number": email_sequence_number,
        "email_status": email_status,
    }
    data = api_request(cfg, "GET", f"/campaigns/{campaign_id}/statistics", params=params)
    emit(data, pretty=cfg.pretty, table_builder=statistics_table)


@analytics_app.command("top")
def analytics_top(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "GET", f"/campaigns/{campaign_id}/analytics")
    emit(data, pretty=cfg.pretty)


@analytics_app.command("by-date")
def analytics_by_date(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    start_date: str = typer.Option(..., "--start-date", help="YYYY-MM-DD"),
    end_date: str = typer.Option(..., "--end-date", help="YYYY-MM-DD"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(
        cfg,
        "GET",
        f"/campaigns/{campaign_id}/analytics-by-date",
        params={"start_date": start_date, "end_date": end_date},
    )
    emit(data, pretty=cfg.pretty)


@leads_app.command("list")
def campaign_leads_list(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    offset: int | None = typer.Option(None, "--offset", help="Pagination offset"),
    limit: int | None = typer.Option(None, "--limit", help="Pagination limit (defaults to config)"),
) -> None:
    cfg: Config = ctx.obj
    params = {"offset": offset, "limit": limit if limit is not None else cfg.default_limit}
    data = api_request(cfg, "GET", f"/campaigns/{campaign_id}/leads", params=params)
    emit(data, pretty=cfg.pretty, table_builder=campaign_leads_table)


@leads_app.command("get")
def campaign_leads_get(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
    page_size: int = typer.Option(
        100, "--page-size", min=1, max=100, help="List page size while searching"
    ),
    max_pages: int = typer.Option(
        20, "--max-pages", min=1, help="Max pages to scan while searching"
    ),
) -> None:
    cfg: Config = ctx.obj
    row = _find_campaign_lead_entry(
        cfg, campaign_id, lead_id, page_size=page_size, max_pages=max_pages
    )
    if row is None:
        print_error(
            "not_found",
            f"Lead {lead_id} not found in campaign {campaign_id} (searched up to {page_size * max_pages} rows)",
        )
        raise typer.Exit(1)
    emit(row, pretty=cfg.pretty)


@leads_app.command("add")
def campaign_leads_add(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    body_json: str | None = typer.Option(None, "--body-json", help="JSON payload or '-' for stdin"),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Path to JSON payload or '-' for stdin"
    ),
) -> None:
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json, body_file)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)
    try:
        CampaignLeadsAddBodyModel.model_validate(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)
    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/leads", json_body=body)
    emit(data, pretty=cfg.pretty)


@leads_app.command("update")
def campaign_leads_update(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
    body_json: str | None = typer.Option(None, "--body-json", help="JSON payload or '-' for stdin"),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Path to JSON payload or '-' for stdin"
    ),
) -> None:
    cfg: Config = ctx.obj
    try:
        body = load_json_input(body_json, body_file)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)
    try:
        CampaignLeadUpdateBodyModel.model_validate(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)
    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/leads/{lead_id}", json_body=body)
    emit(data, pretty=cfg.pretty)


@leads_app.command("patch")
def campaign_leads_patch(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
    email: str | None = typer.Option(None, "--email", help="Override email (usually auto-filled)"),
    first_name: str | None = typer.Option(None, "--first-name", help="Patch first_name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Patch last_name"),
    phone_number: str | None = typer.Option(None, "--phone-number", help="Patch phone_number"),
    company_name: str | None = typer.Option(None, "--company-name", help="Patch company_name"),
    website: str | None = typer.Option(None, "--website", help="Patch website"),
    location: str | None = typer.Option(None, "--location", help="Patch location"),
    linkedin_profile: str | None = typer.Option(
        None, "--linkedin-profile", help="Patch linkedin_profile"
    ),
    company_url: str | None = typer.Option(None, "--company-url", help="Patch company_url"),
    custom_fields_json: str | None = typer.Option(
        None, "--custom-fields-json", help="JSON object for custom_fields or '-' for stdin"
    ),
    custom_fields_file: str | None = typer.Option(
        None, "--custom-fields-file", help="Path to JSON object for custom_fields or '-' for stdin"
    ),
    body_json: str | None = typer.Option(
        None, "--body-json", help="JSON patch object or '-' for stdin"
    ),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Path to JSON patch object or '-' for stdin"
    ),
    page_size: int = typer.Option(
        100, "--page-size", min=1, max=100, help="List page size while resolving current lead"
    ),
    max_pages: int = typer.Option(
        20, "--max-pages", min=1, help="Max pages to scan while resolving current lead"
    ),
) -> None:
    cfg: Config = ctx.obj
    row = _find_campaign_lead_entry(
        cfg, campaign_id, lead_id, page_size=page_size, max_pages=max_pages
    )
    if row is None:
        print_error(
            "not_found",
            f"Lead {lead_id} not found in campaign {campaign_id} (searched up to {page_size * max_pages} rows)",
        )
        raise typer.Exit(1)

    current = _extract_patchable_lead_input(row)
    if not current:
        print_error("not_found", f"Lead {lead_id} found but no patchable lead fields were returned")
        raise typer.Exit(1)

    try:
        patch_obj = maybe_load_json_input(body_json=body_json, body_file=body_file) or {}
        if not isinstance(patch_obj, dict):
            raise ValueError("patch body must be a JSON object")
        custom_fields_obj = (
            maybe_load_json_input(body_json=custom_fields_json, body_file=custom_fields_file)
            if (custom_fields_json is not None or custom_fields_file is not None)
            else None
        )
        if custom_fields_obj is not None and not isinstance(custom_fields_obj, dict):
            raise ValueError("custom_fields must be a JSON object")
    except Exception as exc:
        print_error("validation_error", f"Invalid patch body: {exc}")
        raise typer.Exit(1)

    patch: dict[str, Any] = dict(patch_obj)
    direct_fields = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "company_name": company_name,
        "website": website,
        "location": location,
        "linkedin_profile": linkedin_profile,
        "company_url": company_url,
    }
    for key, value in direct_fields.items():
        if value is not None:
            patch[key] = value
    if custom_fields_obj is not None:
        patch["custom_fields"] = custom_fields_obj

    if not patch:
        print_error(
            "validation_error",
            "Provide at least one patch flag or a JSON patch via --body-json/--body-file",
        )
        raise typer.Exit(1)

    merged = {**current, **patch}
    try:
        CampaignLeadUpdateBodyModel.model_validate(merged)
    except Exception as exc:
        print_error("validation_error", f"Invalid merged update body: {exc}")
        raise typer.Exit(1)

    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/leads/{lead_id}", json_body=merged)
    emit(data, pretty=cfg.pretty)


@leads_app.command("pause")
def campaign_leads_pause(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/leads/{lead_id}/pause")
    emit(data, pretty=cfg.pretty)


@leads_app.command("resume")
def campaign_leads_resume(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
    delay_days: int | None = typer.Option(None, "--delay-days", min=0, help="Resume after N days"),
) -> None:
    cfg: Config = ctx.obj
    body: dict = {}
    if delay_days is not None:
        body["resume_lead_with_delay_days"] = delay_days
    data = api_request(
        cfg, "POST", f"/campaigns/{campaign_id}/leads/{lead_id}/resume", json_body=body
    )
    emit(data, pretty=cfg.pretty)


@leads_app.command("unsubscribe")
def campaign_leads_unsubscribe(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/leads/{lead_id}/unsubscribe")
    emit(data, pretty=cfg.pretty)


@leads_app.command("delete")
def campaign_leads_delete(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    require_yes_or_confirm(yes, f"Delete lead {lead_id} from campaign {campaign_id}?")
    cfg: Config = ctx.obj
    data = api_request(cfg, "DELETE", f"/campaigns/{campaign_id}/leads/{lead_id}")
    emit(data, pretty=cfg.pretty)


@leads_app.command("message-history")
def campaign_leads_message_history(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    lead_id: int = typer.Argument(..., help="Lead ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "GET", f"/campaigns/{campaign_id}/leads/{lead_id}/message-history")
    emit(data, pretty=cfg.pretty)
