import json
from pathlib import Path

from prefect import get_run_logger, task

from jfri.tasks.alpha_vantage.client import get_av_data


@task
def ingest_data_as_json(ingest_path: Path, function: str, params: dict):
    """Ingest data as JSON.

    Combining fetching and writing data into a single task simplifies concurrency for
    flows that backfill data.
    """
    logger = get_run_logger()

    data = get_av_data(function, params)

    if not data.get("data"):
        logger.warning(
            "No data returned for function: %s with params: %s.", function, params
        )
        return

    ingest_path.write_text(json.dumps(data), encoding="utf-8")
