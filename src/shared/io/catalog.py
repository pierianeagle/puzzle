import os
from pathlib import Path
from typing import Literal

Layer = Literal["ingested", "cleaned", "processed"]


def get_catalog_external_directory(layer: Layer, source: str) -> Path:
    """Return the directory holding medallion-layer external data for a source.

    Filenames are intentionally not part of this utility. Flows construct their own
    per-dataset names against the directory returned here.

    Typical usage example:
    >>> get_catalog_external_directory("ingested", "alpha_vantage")
    """
    return Path(os.environ["CATALOG_PATH"]) / "external" / layer / source
