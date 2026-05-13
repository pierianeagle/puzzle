import json
from pathlib import Path

import pandas as pd

from shared.io.catalog import Layer, get_catalog_external_directory

LAYER_EXTENSION: dict[Layer, str] = {
    "ingested": ".json",
    "cleaned": ".parquet",
    "processed": ".parquet",
}


def get_historic_options_chain_filepath(
    layer: Layer, symbol: str, date: pd.Timestamp
) -> Path:
    stem = f"{symbol.lower()}_eod_{date.strftime('%Y_%m_%d')}"

    return get_catalog_external_directory(layer, "alpha_vantage") / (
        stem + LAYER_EXTENSION[layer]
    )


# TODO - This function should reference a cleaned series that's the result of another
# flow.
def load_underlying_close(ticker: str, date: pd.Timestamp) -> float | None:
    """Look up the EOD close for `ticker` on `date` from the ingested OHLC dump."""
    directory = get_catalog_external_directory("ingested", "alpha_vantage")
    candidates = sorted(directory.glob(f"{ticker.lower()}_ohlc_1d_*.json"))

    if not candidates:
        return None

    payload = json.loads(candidates[-1].read_text())

    for row in payload.get("data", []):
        if row.get("date") == date.strftime("%Y-%m-%d"):
            return float(row["close"])

    return None
