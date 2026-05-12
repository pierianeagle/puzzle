import os

import requests
from prefect import task
from prefect.concurrency.sync import rate_limit
from prefect.tasks import exponential_backoff


class AlphaVantageRateLimitError(Exception):
    """Raised when Alpha Vantage returns a rate limit message in the response body."""


class AlphaVantagePlanError(Exception):
    """Raised when Alpha Vantage returns an API plan message in the response body."""


class AlphaVantageError(Exception):
    """Raised when Alpha Vantage returns an error message in the response body."""


@task(
    retries=4,
    retry_delay_seconds=exponential_backoff(2),
    # Don't retry bad requests.
    retry_condition_fn=lambda task, task_run, state: isinstance(
        state.result(raise_on_failure=False),
        AlphaVantageRateLimitError | requests.exceptions.RequestException,
    ),
    timeout_seconds=60,
)
def get_av_data(
    function: str,
    params: dict | None = None,
) -> dict:
    """Fetch JSON data from the Alpha Vantage API.

    This task consumes one slot from the "alpha-vantage" global concurrency limit, which
    must be created before running this task.

    Args:
        function: Function name, e.g. "HISTORICAL_OPTIONS".
        params: Additional query parameters, e.g. {"symbol": "SPX"}.

    Typical usage example:
    >>> prefect gcl create alpha-vantage --limit 5 --slot-decay-per-second 1.25
    >>> data = get_av_data("HISTORICAL_OPTIONS", params={"symbol": "SPX"})
    """
    # Enforce the rate limit server-side (across multiple workers/processes).
    rate_limit("alpha-vantage", occupy=1)

    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": function,
            "apikey": os.environ["ALPHA_VANTAGE_PREMIUM_API_KEY"],
            **(params or {}),
        },
        timeout=30,  # generous for historical options
    )

    response.raise_for_status()

    data = response.json()

    # Because Alpha Vantage always returns HTTP 200 OK, even for errors and rate limits,
    # we need to inspect the response body to detect errors.
    if "Note" in data:
        raise AlphaVantageRateLimitError(data["Note"])

    if "Information" in data:
        if any(
            phrase in data["Information"].lower() for phrase in ("rate limit", "burst")
        ):
            raise AlphaVantageRateLimitError(data["Information"])
        else:
            raise AlphaVantagePlanError(data["Information"])

    if "Error Message" in data:
        raise AlphaVantageError(data["Error Message"])

    return data
