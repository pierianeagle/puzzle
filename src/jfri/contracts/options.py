from datetime import datetime
from typing import Literal
from uuid import UUID

import pandas as pd
import pandera.pandas as pa
from pandera.engines.pandas_engine import DateTime
from pandera.typing.pandas import Series
from pydantic import BaseModel


class OptionsChainMetadata(BaseModel):
    """Metadata for a cleaned EOD options chain.

    Two layers: source provenance (where the data came from, what the upstream API
    said about it) and process provenance (how and when this file was produced).
    """

    source: Literal["av", "cboe"]
    endpoint: str
    message: str | None = None
    source_file_path: str
    source_file_sha256: str

    underlying_price: float | None = None

    ingested: datetime
    processed: datetime
    prefect_flow_version: str
    prefect_flow_run_id: UUID | None = None


class OptionsChain(pa.DataFrameModel):
    """Cleaned EOD options chain for a single symbol and day.

    Columns are flat (no pandas index) so the on-disk Parquet is portable across
    Polars, DuckDB and raw PyArrow readers. Consumers reconstruct an index at the
    point of use.
    """

    option: Series[str] = pa.Field(unique=True)
    symbol: Series[str]
    expiration: Series[DateTime(tz="US/Eastern", unit="ns")] = pa.Field()  # type: ignore
    strike: Series[float] = pa.Field(gt=0)
    type: Series[str] = pa.Field(isin=["call", "put"])

    last_trade_price: Series[float] = pa.Field(ge=0, nullable=True)
    last_trade_time: Series[DateTime(tz="US/Eastern", unit="ns")] = pa.Field(  # type: ignore
        nullable=True
    )

    bid: Series[float] = pa.Field(ge=0, nullable=True)
    ask: Series[float] = pa.Field(ge=0, nullable=True)
    mark: Series[float] = pa.Field(ge=0, nullable=True)

    bid_size: Series[pd.Int64Dtype] = pa.Field(ge=0, nullable=True)
    ask_size: Series[pd.Int64Dtype] = pa.Field(ge=0, nullable=True)
    volume: Series[pd.Int64Dtype] = pa.Field(ge=0, nullable=True)
    open_interest: Series[pd.Int64Dtype] = pa.Field(ge=0, nullable=True)

    implied_volatility: Series[float] = pa.Field(ge=0, nullable=True)
    delta: Series[float] = pa.Field(ge=-1, le=1, nullable=True)
    gamma: Series[float] = pa.Field(ge=0, nullable=True)
    theta: Series[float] = pa.Field(nullable=True)
    vega: Series[float] = pa.Field(ge=0, nullable=True)
    rho: Series[float] = pa.Field(nullable=True)

    class Config:
        coerce = True
        strict = True

    @pa.dataframe_check
    @classmethod
    def non_empty(cls, df: pd.DataFrame) -> bool:
        return len(df) > 0

    @pa.dataframe_check
    @classmethod
    def symbol_constant(cls, df: pd.DataFrame) -> bool:
        return df["symbol"].nunique() == 1

    # @pa.dataframe_check
    # @classmethod
    # def date_constant(cls, df: pd.DataFrame) -> bool:
    #     return df["date"].nunique() == 1

    @pa.dataframe_check
    @classmethod
    def bid_le_ask(cls, df: pd.DataFrame) -> pd.Series:
        """Allow zero-sided quotes; reject genuinely crossed quotes."""
        return (df["bid"] <= df["ask"]) | (df["bid"] == 0) | (df["ask"] == 0)

    # @pa.dataframe_check
    # @classmethod
    # def expiration_ge_date(cls, df: pd.DataFrame) -> pd.Series:
    #     return df["expiration"] >= df["date"]
