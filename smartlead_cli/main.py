"""smartlead CLI root application."""

from __future__ import annotations

from importlib.metadata import version
from typing import Optional

import typer

from smartlead_cli.config import load_config


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"smartlead-cli {version('smartlead-cli')}")
        raise typer.Exit()


from smartlead_cli.commands import campaigns, config_cmd, leads, raw, webhooks  # noqa: E402

app = typer.Typer(
    name="smartlead",
    help="[bold]smartlead[/bold] — Smartlead platform from the command line.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(config_cmd.app, name="config")
app.add_typer(campaigns.app, name="campaigns")
app.add_typer(leads.app, name="leads")
app.add_typer(webhooks.app, name="webhooks")
app.add_typer(raw.app, name="raw")


@app.callback()
def main(
    ctx: typer.Context,
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="SMARTLEAD_API_KEY",
        help="Smartlead API key (overrides config)",
        show_envvar=True,
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        envvar="SMARTLEAD_BASE_URL",
        help="Smartlead API base URL (overrides config)",
        show_envvar=True,
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Render Rich tables / pretty JSON when available"),
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Interact with Smartlead APIs via direct HTTP requests."""
    ctx.ensure_object(dict)
    cfg = load_config(api_key_flag=api_key, base_url_flag=base_url)
    cfg.pretty = pretty
    ctx.obj = cfg
