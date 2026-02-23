"""Raw HTTP request subcommand for unsupported Smartlead endpoints."""

from __future__ import annotations

import json

import typer

from smartlead_cli.args import maybe_load_json_input, parse_json_kv_pairs, parse_kv_pairs
from smartlead_cli.client import api_request
from smartlead_cli.config import Config
from smartlead_cli.output import emit, print_error
from smartlead_cli.serialize import to_data

app = typer.Typer(name="raw", help="Direct API access for unsupported endpoints.", no_args_is_help=True)


@app.command("request")
def raw_request(
    ctx: typer.Context,
    method: str = typer.Option(..., "--method", help="HTTP method (GET, POST, PATCH, DELETE, ...)"),
    path: str = typer.Option(..., "--path", help="API path (e.g. /campaigns) or full URL"),
    query: list[str] = typer.Option([], "--query", help="Query param KEY=VALUE (repeatable)"),
    query_json: list[str] = typer.Option([], "--query-json", help="Query param KEY=<json> (repeatable)"),
    header: list[str] = typer.Option([], "--header", help="Header KEY=VALUE (repeatable)"),
    body_json: str | None = typer.Option(None, "--body-json", help="JSON body or '-' for stdin"),
    body_file: str | None = typer.Option(None, "--body-file", help="Path to JSON body or '-' for stdin"),
    include_meta: bool = typer.Option(False, "--include-meta", help="Include status code and headers in output"),
    no_auth: bool = typer.Option(False, "--no-auth", help="Do not append api_key query parameter"),
) -> None:
    cfg: Config = ctx.obj
    try:
        params: dict = {}
        params.update(parse_json_kv_pairs(query_json))
        params.update(parse_kv_pairs(query))
        headers = parse_kv_pairs(header)
        body = maybe_load_json_input(body_json=body_json, body_file=body_file)
    except Exception as exc:
        print_error("validation_error", f"Invalid raw request arguments: {exc}")
        raise typer.Exit(1)

    data = to_data(
        api_request(
            cfg,
            method,
            path,
            params=params or None,
            headers=headers or None,
            json_body=body,
            require_auth=not no_auth,
            include_meta=include_meta,
        )
    )
    emit(data, pretty=cfg.pretty)


@app.command("examples")
def raw_examples() -> None:
    emit(
        {
            "examples": [
                {"method": "GET", "path": "/campaigns"},
                {"method": "POST", "path": "/campaigns/123/status", "query": {"status": "PAUSED"}},
                {"method": "POST", "path": "/campaigns/123/leads", "body": [{"email": "a@example.com"}]},
            ]
        }
    )
