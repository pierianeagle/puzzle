# jfri

Workflow automation and data pipelines with Prefect.

End-of-day options-chains from two sources are ingested, cleaned, and validated before being stored as Parquet.

## Sources

| Provider | Coverage | Output series|
| - | - | - |
| Alpha Vantage (AV) | Historic EOD quotes back to 2008 | One file per `(symbol, trading_day)` |
| CBOE | Current delayed quotes | One file per `(symbol, trading_day)` where `symbol ∈ {SPX, SPXW}` is produced by ingesting `ticker = SPX` |

### CBOE

I'm currently sourcing data from CBOE's public delayed quotes feed which has a 15 minute delay (which can be checked by comparing `timestamp` to `data.last_trade_time`). True intraday open interest data however, is not publicly available, so that data is stale by definition - it's OPRA's EOD values from the last day.

Their EOD snapshots are taken at 4:15pm ET, not 4:00pm, because SPX options trade until then.

For whatever reason, the top-level `timestamp` is **UTC** (server clock), but per-contract `last_trade_time` (and top-level `data.last_trade_time`) is **US/Eastern** (exchange wall clock).

## Rate and Concurrency limits

A single Prefect **global concurrency limit** named `alpha-vantage` throttles
every outbound AV HTTP call. The `backfill_ingest_historic_options_chain` flow
fans out into a 32-thread pool but each task acquires one slot from this
limit before issuing the request, so the effective request rate is governed
here — not by the thread pool size.

| Field | Value | Meaning |
| - | - | - |
| `--limit` | 5 | Limit in-flight requests at any instant |
| `--slot-decay-per-second` | 1.25 | Slots regenerate at 1.25/s (steady-state cap ≈ **75 requests/minute**) |

This ceiling matches the Alpha Vantage premium tier. The limit is consulted inside
[`tasks/alpha_vantage/client.py`](tasks/alpha_vantage/client.py) via
`rate_limit("alpha-vantage", occupy=1)`, so even ad-hoc calls outside the
backfill flow obey it.

CBOE has no equivalent limit.

## Layout

Data is stored on disk as a folder within Nautilus Trader's `catalog/` (the path of whih I store as an environment variable `CATALOG_PATH`). The layout is medallion-style, with `ingested/`, `cleaned/`, and `processed/` folders organised by source (e.g. `ingested/cboe/`).

The AV cleaner uses `TRANSFORM_VERSION` stored in Parquet metadata so a backfill
re-cleans only files produced by an older transform. The CBOE cleaner has no
such guard — it overwrites today's parquet on every event (today's chain mutates
intraday, so this is intentional).

## Wiring

Every source follows the same general pattern where scheduled `ingest` flows emit
events which subsequent `clean` flows pick up. This is repeated for further `process`
flows.

The event trigger match key is `prefect.resource.id == "jfri"` (which is set by
[`RESOURCE_ID`](__init__.py)).

The deployment / trigger config / event names are currently duplicated in
two places that must stay consistent:
- [main.py](main.py) via `serve(...)` with `DeploymentEventTrigger`
- [prefect.yaml](prefect.yaml) for `prefect deploy`-style registration

## Running

```bash
# 1. Start the prefect server (long-lived).
prefect server start --host 127.0.0.1 --port 4200

# 2. One-time setup against that server (in another shell).
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
prefect gcl create alpha-vantage --limit 5 --slot-decay-per-second 1.25

# 3. Register and serve all deployments.
PYTHONPATH=src python -m jfri.main
```

`python -m jfri.main` calls `prefect.serve(...)` which both registers and runs
the deployments in-process (no separate worker needed).

The cron schedules (`30 16 * * 1-5`, America/New_York) on both ingest
deployments fire shortly after the US equity close.
