import json
from pathlib import Path

from prefect import get_run_logger, task

from jfri.tasks.cboe.client import get_cboe_options_chain


@task
def ingest_todays_historic_options_chain(ingest_path: Path, ticker: str):
    """Ingest today's historic EOD options chain as JSON."""
    logger = get_run_logger()

    data = get_cboe_options_chain(ticker)

    if not data.get("data"):
        logger.warning(
            "No data returned ticker: %s.",
            ticker,
        )
        return

    ingest_path.write_text(json.dumps(data), encoding="utf-8")
