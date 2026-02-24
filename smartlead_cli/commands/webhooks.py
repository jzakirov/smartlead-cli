"""Campaign webhooks helper commands."""

import typer

from smartlead_cli.args import load_json_input
from smartlead_cli.client import api_request
from smartlead_cli.confirm import require_yes_or_confirm
from smartlead_cli.config import Config
from smartlead_cli.output import emit, print_error, webhooks_table
from smartlead_cli.schemas import CampaignWebhookUpsertBodyModel, SMARTLEAD_WEBHOOK_EVENT_TYPES

WEBHOOK_EVENT_TYPES_HELP = ", ".join(SMARTLEAD_WEBHOOK_EVENT_TYPES)

app = typer.Typer(
    name="webhooks",
    help="Campaign webhook operations. Use `upsert` with a JSON body.",
    no_args_is_help=True,
)


@app.command("list")
def webhooks_list(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "GET", f"/campaigns/{campaign_id}/webhooks")
    emit(data, pretty=cfg.pretty, table_builder=webhooks_table)


@app.command(
    "upsert",
    help=(
        "Add/update a campaign webhook. "
        f"`event_types` allowed values: {WEBHOOK_EVENT_TYPES_HELP}. "
        "`categories` must be a non-empty list of Smartlead lead category names "
        "(workspace-specific/custom labels)."
    ),
)
def webhooks_upsert(
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
        CampaignWebhookUpsertBodyModel.model_validate(body)
    except Exception as exc:
        print_error("validation_error", f"Invalid request body: {exc}")
        raise typer.Exit(1)
    data = api_request(cfg, "POST", f"/campaigns/{campaign_id}/webhooks", json_body=body)
    emit(data, pretty=cfg.pretty)


@app.command("delete")
def webhooks_delete(
    ctx: typer.Context,
    campaign_id: int = typer.Argument(..., help="Campaign ID"),
    webhook_id: int = typer.Option(..., "--webhook-id", help="Webhook ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
) -> None:
    require_yes_or_confirm(yes, f"Delete webhook {webhook_id} from campaign {campaign_id}?")
    cfg: Config = ctx.obj
    data = api_request(
        cfg, "DELETE", f"/campaigns/{campaign_id}/webhooks", json_body={"id": webhook_id}
    )
    emit(data, pretty=cfg.pretty)
