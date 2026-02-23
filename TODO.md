# TODO (Smartlead CLI backlog)

## High priority

- Add `campaigns sequences get/save` curated commands
- Add lead export helper (`campaigns leads-export`) for CSV download
- Add global blocklist helpers (add/list/remove)
- Add lead categories helpers (confirm endpoint shapes and scopes)
- Add client CRUD helpers (if needed for multi-tenant workflows)

## UX improvements

- Add `smartlead raw examples`
- Add shell completion docs / install helpers
- Add `--output json|pretty` switch (currently `--pretty` boolean)
- Add confirmation bypass config defaults (still keep `--yes` safety)

## Resilience

- Smarter retry behavior based on endpoint idempotency
- Optional jittered backoff
- Better error detail extraction for non-JSON responses

## Docs

- Endpoint coverage matrix (curated vs raw-only)
- Copy/paste request body templates for common lead import flows
