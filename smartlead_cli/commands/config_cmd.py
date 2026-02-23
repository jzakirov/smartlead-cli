"""config subcommand: show / set / init."""

import sys

import typer
from rich.console import Console
from rich.prompt import Prompt

from smartlead_cli.client import api_request
from smartlead_cli.config import (
    Config,
    CONFIG_PATH,
    config_as_dict,
    load_config,
    save_config,
    save_config_key,
)
from smartlead_cli.output import print_error, print_json

app = typer.Typer(name="config", help="Manage smartlead CLI configuration.", no_args_is_help=True)
console = Console()


@app.command("show")
def config_show(
    ctx: typer.Context,
    reveal: bool = typer.Option(False, "--reveal", help="Show full API key."),
) -> None:
    cfg: Config = ctx.obj
    print_json(config_as_dict(cfg, reveal=reveal))


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dotted config key, e.g. core.retries"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    try:
        save_config_key(key, value)
        print_json({"ok": True, "key": key, "value": value})
    except Exception as exc:
        print_error("config_error", f"Failed to write config: {exc}")
        raise typer.Exit(1)


@app.command("init")
def config_init(
    ctx: typer.Context,
    skip_validation: bool = typer.Option(
        False,
        "--skip-validation",
        help="Save config without validating the API key (useful offline).",
    ),
) -> None:
    if not sys.stdin.isatty():
        print_error("validation_error", "`smartlead config init` requires an interactive terminal.")
        raise typer.Exit(1)

    cfg: Config = ctx.obj
    console.print("[bold]smartlead setup wizard[/bold]")
    console.print(f"Config will be saved to: [dim]{CONFIG_PATH}[/dim]\n")

    api_key = Prompt.ask("Smartlead API key", password=True, default=cfg.api_key or "")
    base_url = Prompt.ask("API base URL", default=cfg.base_url)

    if not api_key:
        print_error("validation_error", "Smartlead API key is required.")
        raise typer.Exit(1)

    new_cfg = load_config()
    new_cfg.api_key = api_key
    new_cfg.base_url = base_url or new_cfg.base_url

    if not skip_validation:
        console.print("\nValidating token with `GET /campaigns`…")
        try:
            result = api_request(new_cfg, "GET", "/campaigns")
            count = len(result) if isinstance(result, list) else None
            if count is not None:
                console.print(f"[green]✓[/green] Token is valid (received {count} campaigns)")
            else:
                console.print("[green]✓[/green] Token is valid")
        except typer.Exit:
            raise
        except Exception as exc:
            print_error("auth_error", f"Validation failed: {exc}")
            raise typer.Exit(1)
    else:
        console.print("\n[dim]Skipping token validation (--skip-validation)[/dim]")

    save_config(new_cfg)
    console.print(f"\n[green]✓[/green] Config saved to {CONFIG_PATH}")
    print_json(config_as_dict(new_cfg))
