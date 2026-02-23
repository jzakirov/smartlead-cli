"""campaigns subcommand (campaigns, analytics, and campaign leads)."""

import typer

from smartlead_cli.args import load_json_input
from smartlead_cli.client import api_request
from smartlead_cli.config import Config
from smartlead_cli.output import (
    campaign_leads_table,
    campaigns_table,
    emit,
    print_error,
    statistics_table,
)

app = typer.Typer(name="campaigns", help="Smartlead campaign operations.", no_args_is_help=True)
analytics_app = typer.Typer(
    name="analytics", help="Campaign analytics helpers.", no_args_is_help=True
)
leads_app = typer.Typer(name="leads", help="Campaign lead operations.", no_args_is_help=True)

app.add_typer(analytics_app, name="analytics")
app.add_typer(leads_app, name="leads")


@app.command("list")
def campaigns_list(
    ctx: typer.Context,
    offset: int | None = typer.Option(None, "--offset", help="Pagination offset"),
    limit: int | None = typer.Option(None, "--limit", help="Pagination limit (defaults to config)"),
) -> None:
    cfg: Config = ctx.obj
    params = {"offset": offset, "limit": limit if limit is not None else cfg.default_limit}
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

    data = api_request(cfg, "POST", "/campaigns/create", json_body=body)
    emit(data, pretty=cfg.pretty)


@app.command("delete")
def campaigns_delete(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    yes: bool = typer.Option(False, "--yes", help="Confirm deletion"),
) -> None:
    if not yes:
        print_error("validation_error", "Deletion requires --yes")
        raise typer.Exit(1)
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
    data = api_request(cfg, "PATCH", f"/campaigns/{campaign_id}/leads/{lead_id}", json_body=body)
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
    yes: bool = typer.Option(False, "--yes", help="Confirm deletion"),
) -> None:
    if not yes:
        print_error("validation_error", "Deletion requires --yes")
        raise typer.Exit(1)
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
