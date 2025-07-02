import pandas as pd


def read_dataframe_with_metadata_from_hdf(
    filepath: str,
    df: pd.DataFrame,
    key: str = "data",
) -> tuple[pd.DataFrame, dict]:
    """Read a DataFrame with JSON metadata from HDF5 using Pandas."""
    with pd.HDFStore(filepath) as store:
        df = store[key]
        metadata = store.get_storer(key).attrs.metadata

    return df, metadata


def write_dataframe_with_metadata_to_hdf(
    filepath: str,
    df: pd.DataFrame,
    key: str = "data",
    **metadata,
) -> None:
    """Write a DataFrame with JSON metadata to HDF5 using Pandas.

    The metadata is stored as an attribute of the "data" dataset in the HDF5 file.

    Typical usage example:
    >>> metadata = {"local_tz": "Europe/London"}
    ... write_dataframe_with_metadata_to_hdf(filepath, df, **metadata)
    """
    store = pd.HDFStore(filepath)
    store.put(key, df)
    store.get_storer(key).attrs.metadata = metadata
    store.close()
