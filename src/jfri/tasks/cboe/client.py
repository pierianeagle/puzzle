import requests
from prefect import task
from prefect.tasks import exponential_backoff


@task(
    retries=4,
    retry_delay_seconds=exponential_backoff(2),
    timeout_seconds=60,
)
def get_cboe_options_chain(ticker: str) -> dict:
    """Fetch the latest delayed-quote options chain for from CBOE.

    The response may bundle multiple OCC tickers. For example, SPX returns SPX monthlies
    and SPXW weeklies.
    """
    response = requests.get(
        f"https://cdn.cboe.com/api/global/delayed_quotes/options/_{ticker}.json",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()
