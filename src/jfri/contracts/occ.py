"""OCC OSI ticker parsing.

The Options Clearing Corporation's standard symbol format encodes underlying,
expiration, type, and strike in one 21-char string e.g. `SPXW260515P00200000`.

- 1-6 chars : underlying / series identifier (variable length, no spaces in our feeds)
- 6 digits  : expiration as YYMMDD
- 1 char    : `C` (call) or `P` (put)
- 8 digits  : zero-padded strike *1000
"""

import re
import warnings
from datetime import date
from typing import Literal, NamedTuple

import pandas as pd

OCC_TICKER_RE = re.compile(
    r"^(?P<u>[A-Z]+)(?P<y>\d{2})(?P<m>\d{2})(?P<d>\d{2})(?P<t>[CP])(?P<s>\d{8})$"
)

OPTION_TYPE_MAP = {"C": "call", "P": "put"}


class OccTicker(NamedTuple):
    underlying: str
    expiration: date
    type: Literal["call", "put"]
    strike: float


def parse_occ_ticker(ticker: str) -> OccTicker:
    """Parse an OCC OSI ticker."""
    match = OCC_TICKER_RE.match(ticker)

    if match is None:
        raise ValueError(f"Not a valid OCC OSI ticker: {ticker!r}")

    return OccTicker(
        underlying=match["u"],
        expiration=date(2000 + int(match["y"]), int(match["m"]), int(match["d"])),
        type=OPTION_TYPE_MAP[match["t"]],
        strike=int(match["s"]) / 1000,
    )


def parse_occ_tickers(options: pd.Series) -> pd.DataFrame:
    """Parse a series of OCC OSI tickers.

    Returns:
        A DataFrame aligned to `options.index`.
    """
    df_parsed = options.str.extract(OCC_TICKER_RE)

    failed = options[df_parsed["u"].isna()]

    if not failed.empty:
        warnings.warn(
            f"Failed to parse {len(failed)} OCC OSI ticker(s):\n{failed.to_string()}",
            stacklevel=2,
        )

    return pd.DataFrame(
        data={
            "underlying": df_parsed["u"],
            "expiration": pd.to_datetime(
                "20" + df_parsed["y"] + "-" + df_parsed["m"] + "-" + df_parsed["d"]
            ),
            "type": df_parsed["t"].map(OPTION_TYPE_MAP),
            "strike": df_parsed["s"].astype("Int64") / 1000,
        },
        index=options.index,
    )
