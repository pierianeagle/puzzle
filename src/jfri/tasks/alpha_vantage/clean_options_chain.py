import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pandera.typing.pandas import DataFrame
from prefect import task
from prefect.runtime import flow_run

from jfri.contracts.options import OptionsChain, OptionsChainMetadata
from jfri.tasks.clean_options_chain import (
    find_invalid_rows,
    find_mismatched_rows,
    resolve_bad_rows,
    resolve_duplicate_contracts,
)
from shared.io.arrow import write_dataframe_with_metadata_to_parquet

TRANSFORM_VERSION = "1.2.0"

RENAMES = {
    "contractID": "option",
}

FLOAT_COLUMNS = (
    "strike",
    "last",
    "mark",
    "bid",
    "ask",
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
def read_ingested_data_and_validate_metadata(
    ingested_path: Path,
) -> tuple[OptionsChainMetadata, pd.DataFrame]:
    """Read an ingested EOD options chain and validate its metadata.

    The returned dataframe is still all-strings with sentinels for missing greeks.
    Further validation happens in `clean_and_validate_data`.
    """
    raw_bytes = ingested_path.read_bytes()

    payload = json.loads(raw_bytes)
    records = payload["data"]

    df_ingested = pd.DataFrame.from_records(records)

    metadata = OptionsChainMetadata(
        source="av",
        endpoint=payload["endpoint"],
        message=payload["message"],
        source_file_path=str(ingested_path),
        source_file_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        processed=datetime.now(UTC),
        prefect_flow_version=TRANSFORM_VERSION,
        prefect_flow_run_id=flow_run.get_id(),
    )

    return metadata, df_ingested


@task
def clean_and_validate_data(
    df_ingested: pd.DataFrame,
) -> DataFrame[OptionsChain]:
    """Clean and validate an ingested EOD options chain."""
    df = df_ingested.rename(columns=RENAMES)

    # Older historic data occasionally emits CALL/PUT instead of call/put.
    df["type"] = df["type"].str.lower()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize("US/Eastern")
    df["expiration"] = pd.to_datetime(df["expiration"]).dt.tz_localize("US/Eastern")

    df = resolve_duplicate_contracts(df)

    sr_invalid = find_invalid_rows(df)
    sr_mismatched = find_mismatched_rows(df)
    df = resolve_bad_rows(df, sr_invalid | sr_mismatched)

    schema_columns = list(OptionsChain.to_schema().columns)

    return OptionsChain.validate(df[schema_columns])


@task
def clean_historic_options_chain(ingested_path: Path, cleaned_path: Path):
    """Promote an ingested JSON file with an EOD options chain to cleaned Parquet.

    Combining fetching and writing data into a single task simplifies concurrency for
    flows that backfill data.
    """
    metadata, df_ingested = read_ingested_data_and_validate_metadata(ingested_path)

    df = clean_and_validate_data(df_ingested)

    write_dataframe_with_metadata_to_parquet(
        cleaned_path, df, **metadata.model_dump(mode="json")
    )
