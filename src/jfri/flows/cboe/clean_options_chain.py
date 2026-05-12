import pandas as pd
from prefect import flow

from jfri.tasks.cboe.catalog import get_historic_options_chain_filepath
from jfri.tasks.cboe.clean_options_chain import clean_todays_options_chain


@flow
def clean_todays_options_chain_flow(ticker: str, symbol: str, date: str) -> None:
    """Promote an ingested EOD options chain to Parquet.

    This flow will re-process the given day's data.

    `ticker` is the URL-level identifier the file was fetched with (e.g. `SPX`),
    `symbol` is the OCC underlying to extract (e.g. `SPX` or `SPXW`). Each invocation
    produces one file per symbol. Bundled responses are split by calling this task once
    per discovered symbol.
    """
    date = pd.Timestamp(date)

    ingested_path = get_historic_options_chain_filepath("ingested", ticker, date)
    cleaned_path = get_historic_options_chain_filepath("cleaned", symbol, date)

    clean_todays_options_chain(ingested_path, cleaned_path, symbol, ticker)
