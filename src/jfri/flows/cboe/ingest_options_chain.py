import pandas as pd
from prefect import flow
from prefect.events import emit_event

from jfri import RESOURCE_ID
from jfri.tasks.cboe.catalog import get_historic_options_chain_filepath
from jfri.tasks.cboe.ingest_options_chain import get_unique_symbols
from jfri.tasks.cboe.ingest_options_chain import (
    ingest_todays_options_chain as ingest_todays_options_chain_task,
)

INGESTED_EVENT = "cboe.ingested_todays_options_chain"


@flow
def ingest_todays_options_chain(ticker: str) -> None:
    """Ingest today's EOD options chain for `ticker` and emit one event per series.

    This flow will overwrite today's data.
    """
    date = pd.Timestamp.now(tz="US/Eastern").normalize()
    iso_date = date.strftime("%Y-%m-%d")

    ingested_path = get_historic_options_chain_filepath("ingested", ticker, date)

    ingest_todays_options_chain_task(ingested_path, ticker)

    if ingested_path.exists():
        symbols = get_unique_symbols(ingested_path)

        for symbol in symbols:
            emit_event(
                event=INGESTED_EVENT,
                resource={"prefect.resource.id": RESOURCE_ID},
                payload={"ticker": ticker, "symbol": symbol, "date": iso_date},
            )
