import pandas as pd
from prefect import flow, get_run_logger
from prefect.events import emit_event
from prefect.task_runners import ThreadPoolTaskRunner

from jfri import RESOURCE_ID
from jfri.tasks.alpha_vantage.catalog import get_historic_options_chain_filepath
from jfri.tasks.alpha_vantage.ingest_data_as_json import ingest_data_as_json

INGESTED_EVENT = "alpha_vantage.ingested_historic_options_chain"


@flow
def ingest_historic_options_chain(
    symbol: str, date: str | None = None, params: dict | None = None
):
    """Ingest a historic EOD options chain as JSON.

    `date` is an ISO string (YYYY-MM-DD) so cron- and YAML-driven deployments can
    supply it. Defaulting to today lets the daily cron fire with no params.
    """
    date = pd.Timestamp(date) if date else pd.Timestamp.now().normalize()
    iso_date = date.strftime("%Y-%m-%d")

    ingested_path = get_historic_options_chain_filepath("ingested", symbol, date)

    ingest_data_as_json(
        ingested_path,
        "HISTORICAL_OPTIONS",
        {"symbol": symbol, "date": iso_date, **(params or {})},
    )

    if ingested_path.exists():
        emit_event(
            event=INGESTED_EVENT,
            resource={"prefect.resource.id": RESOURCE_ID},
            payload={"symbol": symbol, "date": iso_date},
        )


@flow(task_runner=ThreadPoolTaskRunner(max_workers=32))
def backfill_ingest_historic_options_chain(symbol: str, params: dict | None = None):
    """Backfill ingesting every missing historic EOD options chain as JSON.

    This flow runs all tasks in parallel, bounded by the "alpha-vantage" global
    concurrency limit, instead of calling subflows sequentially.
    """
    logger = get_run_logger()

    dates = pd.bdate_range(pd.Timestamp("2008-01-01"), pd.Timestamp.now())

    missing = [
        date
        for date in dates
        if not get_historic_options_chain_filepath("ingested", symbol, date).exists()
    ]

    logger.info(
        "Backfilling %d trading days (%d already on disk).",
        len(missing),
        len(dates) - len(missing),
    )

    futures = [
        ingest_data_as_json.submit(
            get_historic_options_chain_filepath("ingested", symbol, date),
            "HISTORICAL_OPTIONS",
            {"symbol": symbol, "date": date.strftime("%Y-%m-%d"), **(params or {})},
        )
        for date in missing
    ]

    for future in futures:
        future.wait()
