"""Global lead helper commands."""

import typer

from smartlead_cli.client import api_request
from smartlead_cli.config import Config
from smartlead_cli.output import emit

app = typer.Typer(name="leads", help="Global lead operations.", no_args_is_help=True)


@app.command("get-by-email")
def get_lead_by_email(
    ctx: typer.Context,
    email: str = typer.Option(..., "--email", help="Lead email"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "GET", "/leads", params={"email": email})
    emit(data, pretty=cfg.pretty)


@app.command("unsubscribe-all")
def unsubscribe_lead_globally(
    ctx: typer.Context,
    lead_id: int = typer.Argument(..., help="Lead ID"),
) -> None:
    cfg: Config = ctx.obj
    data = api_request(cfg, "POST", f"/leads/{lead_id}/unsubscribe")
    emit(data, pretty=cfg.pretty)
