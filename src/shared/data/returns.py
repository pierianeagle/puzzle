from typing import Literal

import pandas as pd


def get_returns(equities: pd.Series) -> pd.Series:
    return equities.pct_change().fillna(0)


def get_cumulative_returns(
    data: pd.Series, method: Literal["returns", "equities"] = "returns"
) -> pd.Series:
    if method == "returns":
        return (1 + data).cumprod() - 1
    elif method == "equities":
        return (data / data.iloc[0]) - 1
    else:
        raise ValueError(
            f"Invalid method. Choose one of: "
            f"{get_cumulative_returns.__annotations__['method'].__args__}"
        )
