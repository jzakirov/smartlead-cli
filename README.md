# smartlead-cli

`smartlead-cli` provides a `smartlead` command for working with the Smartlead API from a terminal.

It follows the same project structure as `plane-cli` and `wildberries-cli`: Typer commands, a shared config layer, JSON-first output, and a `raw` command for full API coverage.

## Install

```bash
pip install smartlead-cli
```

## Authentication

Smartlead uses an API key passed as `api_key` query parameter. Configure it once:

```bash
smartlead config init
```

You can also override at runtime:

```bash
SMARTLEAD_API_KEY=... smartlead campaigns list
```

## Config

Config file path:

- `~/.config/smartlead-cli/config.toml`

Supported keys (examples):

- `core.api_key`
- `core.base_url`
- `core.timeout_seconds`
- `core.retries`
- `defaults.limit`

Examples:

```bash
smartlead config show
smartlead config set core.timeout_seconds 30
smartlead config set core.retries 3
smartlead config set defaults.limit 100
```

## Commands (v1)

- `config` - manage local config
- `campaigns` - list/get/create/delete/update status + analytics/statistics + campaign leads
- `leads` - a few global lead operations
- `webhooks` - campaign webhook helpers
- `raw` - direct API access for unsupported endpoints

## Examples

```bash
smartlead campaigns list
smartlead campaigns list --client-id 123
smartlead campaigns list --include-tags
smartlead campaigns get 12345
smartlead campaigns create --name "New Campaign"
smartlead campaigns status 12345 --status PAUSED
smartlead campaigns statistics 12345 --limit 50 --offset 0
smartlead campaigns analytics top 12345
smartlead campaigns analytics by-date 12345 --start-date 2025-01-01 --end-date 2025-01-31
```

Campaign leads:

```bash
smartlead campaigns leads list 12345
smartlead campaigns leads add 12345 --body-file leads.json
smartlead campaigns leads update 12345 67890 --body-file lead-update.json
smartlead campaigns leads pause 12345 67890
smartlead campaigns leads resume 12345 67890 --delay-days 2
smartlead campaigns leads unsubscribe 12345 67890
smartlead campaigns leads delete 12345 67890 --yes
smartlead campaigns leads message-history 12345 67890
```

Global lead helpers:

```bash
smartlead leads get-by-email --email person@example.com
smartlead leads unsubscribe-all 67890
```

Campaign webhooks:

```bash
smartlead webhooks list 12345
smartlead webhooks upsert 12345 --body-file webhook.json
smartlead webhooks delete 12345 --webhook-id 555 --yes
```

Raw endpoint access (fallback for full API surface):

```bash
smartlead raw request --method GET --path /campaigns
smartlead raw request --method POST --path /campaigns/12345/status --query status=PAUSED
smartlead raw request --method POST --path /campaigns/12345/leads --body-file leads.json
```

## Output

- Default output is JSON on stdout
- Errors are structured JSON on stderr
- Use `--pretty` for Rich tables on selected list commands

## Publishing to PyPI

The repo includes a GitHub Actions workflow (`.github/workflows/publish.yml`) for trusted publishing on tags matching `v*`.

## Notes

- Smartlead API docs (official): https://helpcenter.smartlead.ai/en/articles/125-full-api-documentation
- Smartlead API base URL defaulted in this CLI: `https://server.smartlead.ai/api/v1`
- Rate limiting is handled with simple retries/backoff for `429` and `5xx`
