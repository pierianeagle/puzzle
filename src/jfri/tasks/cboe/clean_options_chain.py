import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pandera.typing.pandas import DataFrame
from prefect import task
from prefect.runtime import flow_run

from jfri.contracts.occ import parse_occ_tickers
from jfri.contracts.options import OptionsChain, OptionsChainMetadata
from jfri.tasks.clean_options_chain import (
    find_invalid_rows,
    find_mismatched_rows,
    resolve_bad_rows,
    resolve_duplicate_contracts,
)
from shared.io.arrow import write_dataframe_with_metadata_to_parquet

TRANSFORM_VERSION = "1.1.0"

RENAMES = {
    "iv": "implied_volatility",
    "theo": "mark",  # theoretical
    "last_trade_price": "last",
}

FLOAT_COLUMNS = (
    "bid",
    "ask",
    "last",
    "implied_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
)

INT_COLUMNS = (
    "bid_size",
    "ask_size",
    "volume",
    "open_interest",
)

NUMERIC_COLUMNS = [*FLOAT_COLUMNS, *INT_COLUMNS]


@task
def clean_and_validate_data(
    df_ingested: pd.DataFrame, symbol: str, timestamp: pd.Timestamp
) -> DataFrame[OptionsChain]:
    """Clean and validate an ingested EOD options chain."""
    df = df_ingested.rename(columns=RENAMES)

    df_parsed = parse_occ_tickers(df["option"])

    # Separate weeklies.
    df = df.loc[df_parsed["underlying"] == symbol].reset_index(drop=True)
    df_parsed = df_parsed.loc[df_parsed["underlying"] == symbol].reset_index(drop=True)

    df["symbol"] = df_parsed["underlying"]
    df["expiration"] = df_parsed["expiration"].dt.tz_localize("US/Eastern")
    df["strike"] = df_parsed["strike"].astype("float64")
    df["type"] = df_parsed["type"]
    df["date"] = timestamp.normalize()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = resolve_duplicate_contracts(df)

    sr_invalid = find_invalid_rows(df)
    sr_mismatched = find_mismatched_rows(df)
    df = resolve_bad_rows(df, sr_invalid | sr_mismatched)

    schema_columns = list(OptionsChain.to_schema().columns)

    return OptionsChain.validate(df[schema_columns])


@task
def clean_todays_options_chain(
    ingested_path: Path, cleaned_path: Path, symbol: str, ticker: str
) -> None:
    """Promote an ingested JSON file to cleaned, series-specific Parquet.

    `ticker` is the URL-level identifier the file was fetched with (e.g. `SPX`),
    `symbol` is the OCC underlying to extract (e.g. `SPX` or `SPXW`). Each invocation
    produces one file per symbol. Bundled responses are split by calling this task once
    per discovered symbol.
    """
    raw_bytes = ingested_path.read_bytes()

    payload = json.loads(raw_bytes)
    records = payload["data"]["options"]

    df_ingested = pd.DataFrame.from_records(records)

    df = clean_and_validate_data(
        df_ingested, symbol, pd.Timestamp(payload["timestamp"], tz="US/Eastern")
    )

    metadata = OptionsChainMetadata(
        source="cboe",
        endpoint=f"/api/global/delayed_quotes/options/_{ticker}.json",
        source_file_path=str(ingested_path),
        source_file_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        processed=datetime.now(UTC),
        prefect_flow_version=TRANSFORM_VERSION,
        prefect_flow_run_id=flow_run.get_id(),
    )

    write_dataframe_with_metadata_to_parquet(
        cleaned_path, df, **metadata.model_dump(mode="json")
    )
