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

    return get_catalog_external_directory(layer, "cboe") / (
        stem + LAYER_EXTENSION[layer]
    )
