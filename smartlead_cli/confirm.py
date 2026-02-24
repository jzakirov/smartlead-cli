"""Interactive confirmation helpers for destructive CLI actions."""

import sys

import typer

from smartlead_cli.output import print_error


def require_yes_or_confirm(yes: bool, prompt: str) -> None:
    """Allow interactive confirmation, require --yes in non-interactive mode."""

    if yes:
        return

    if sys.stdin.isatty():
        confirmed = typer.confirm(prompt, default=False)
        if confirmed:
            return
        print_error("confirmation_required", "Deletion cancelled")
        raise typer.Exit(1)

    print_error("confirmation_required", "Deletion requires --yes in non-interactive mode")
    raise typer.Exit(1)
