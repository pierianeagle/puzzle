import json
from pathlib import Path

import pandas as pd
from prefect import get_run_logger, task

from jfri.contracts.occ import parse_occ_tickers
from jfri.tasks.cboe.client import get_cboe_options_chain


@task
def ingest_todays_options_chain(ingested_path: Path, ticker: str):
    """Ingest today's EOD options chain as JSON."""
    logger = get_run_logger()

    data = get_cboe_options_chain(ticker)

    if not data.get("data"):
        logger.warning(
            "No data returned ticker: %s.",
            ticker,
        )
        return

    ingested_path.write_text(json.dumps(data), encoding="utf-8")


@task
def get_unique_symbols(ingested_path: Path):
    """Return the unique symbols EOD options chain as JSON."""
    payload = json.loads(ingested_path.read_bytes())
    records = payload["data"]["options"]

    df_ingested = pd.DataFrame.from_records(records)

    symbols = parse_occ_tickers(df_ingested["option"])["underlying"].unique()

    return symbols
