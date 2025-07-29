import json
from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def read_feather_data_from_catalog(
    filepath: Path,
    dtype: Literal["pandas", "arrow"] = "pandas",
) -> pd.DataFrame:
    """Read feather data that's been saved to the catalog."""
    with open(filepath, "rb") as f:
        stream = pa.ipc.open_stream(f)
        table = stream.read_all()

    if dtype == "arrow":
        return table

    elif dtype == "pandas":
        df = table.to_pandas()

        df.index = pd.to_datetime(df["ts_init"], unit="ns", origin="unix")

        df = df.drop(columns=["ts_init"])

        return df

    else:
        raise ValueError(
            f"Invalid dtype. Choose one of: "
            f"{read_feather_data_from_catalog.__annotations__['dtype'].__args__}"
        )


def read_dataframe_with_metadata_from_parquet(
    filepath: str,
    key: str = "metadata",
) -> tuple[pd.DataFrame, dict]:
    """Read a DataFrame with JSON metadata from Parquet using PyArrow."""
    table = pq.read_table(filepath)
    df = table.to_pandas()
    metadata_string = table.schema.metadata[key.encode()]
    metadata = json.loads(metadata_string)

    return df, metadata


def write_dataframe_with_metadata_to_parquet(
    filepath: str,
    df: pd.DataFrame,
    key: str = "metadata",
    compression: Literal["NONE", "SNAPPY", "GZIP", "BROTLI", "LZ4", "ZSTD"] = "GZIP",
    **metadata,
) -> None:
    """Write a DataFrame with JSON metadata to Parquet using PyArrow.

    The metadata is stored under the "metadata" key.

    Typical usage example:
    >>> metadata = {"local_tz": "Europe/London"}
    ... write_dataframe_with_metadata_to_parquet(filepath, df, **metadata)
    """
    table = pa.Table.from_pandas(df)

    combined_meta = {
        # Both the key and contents should be encoded as bytes.
        key.encode(): json.dumps(metadata).encode(),
        **table.schema.metadata,
    }

    table = table.replace_schema_metadata(combined_meta)
    pq.write_table(table, filepath, compression=compression)
