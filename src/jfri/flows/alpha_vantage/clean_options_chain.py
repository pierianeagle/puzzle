import re
from pathlib import Path

import pandas as pd
from prefect import flow, get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner

from jfri.tasks.alpha_vantage.catalog import get_historic_options_chain_filepath
from jfri.tasks.alpha_vantage.clean_options_chain import (
    TRANSFORM_VERSION,
)
from jfri.tasks.alpha_vantage.clean_options_chain import (
    clean_historic_options_chain as clean_historic_options_chain_task,
)
from shared.io.arrow import read_dataframe_with_metadata_from_parquet
from shared.io.catalog import get_catalog_external_directory


@flow
def clean_historic_options_chain(symbol: str, date: str) -> None:
    """Promote an ingested historic EOD options chain to Parquet.

    This flow will re-process the given day's data.

    `date` is an ISO string (YYYY-MM-DD) so the event-trigger payload from
    `ingest_historic_options_chain_task` flows through directly.
    """
    date = pd.Timestamp(date)

    ingested_path = get_historic_options_chain_filepath("ingested", symbol, date)
    cleaned_path = get_historic_options_chain_filepath("cleaned", symbol, date)

    clean_historic_options_chain_task(ingested_path, cleaned_path)


def _needs_cleaning(symbol: str, date: pd.Timestamp) -> bool:
    """A day needs cleaning if no Parquet exists, or if `TRANSFORM_VERSION` is stale."""
    cleaned_path = get_historic_options_chain_filepath("cleaned", symbol, date)

    if not cleaned_path.exists():
        return True

    _, metadata = read_dataframe_with_metadata_from_parquet(cleaned_path)

    return metadata.get("prefect_flow_version") != TRANSFORM_VERSION


@flow(task_runner=ThreadPoolTaskRunner(max_workers=32))
def backfill_clean_historic_options_chain(symbol: str) -> None:
    """Backfill promoting every necessary ingested EOD options chain to Parquet."""
    logger = get_run_logger()

    ingested_directory = get_catalog_external_directory("ingested", "alpha_vantage")

    pairs: list[tuple[pd.Timestamp, Path]] = []

    historic_options_chain_filepath_re = re.compile(
        r"^(?P<symbol>.+)_eod_(?P<date>\d{4}_\d{2}_\d{2})\.json$"
    )
    for filepath in ingested_directory.glob(f"{symbol.lower()}_eod_*.json"):
        match = historic_options_chain_filepath_re.match(filepath.name)

        if match is None:
            continue

        pairs.append((pd.Timestamp(match["date"].replace("_", "-")), filepath))

    missing = [
        (date, filepath)
        for date, filepath in sorted(pairs)
        if _needs_cleaning(symbol, date)
    ]

    logger.info(
        "Cleaning %d trading days (%d already on disk at v%s).",
        len(missing),
        len(pairs) - len(missing),
        TRANSFORM_VERSION,
    )

    futures = [
        clean_historic_options_chain_task.submit(
            ingested_path,
            get_historic_options_chain_filepath("cleaned", symbol, date),
        )
        for date, ingested_path in missing
    ]

    for future in futures:
        future.wait()
