import pandas as pd
from prefect import get_run_logger

from jfri.contracts.occ import parse_occ_tickers


def resolve_duplicate_contracts(df: pd.DataFrame) -> pd.DataFrame:
    """Pick the most-active row per contract when duplicates are emitted.

    The correct row is assumed to have (in descending priority) 1) non-zero quote sizes,
    2) non-zero volume, 3) non-zero open interest.
    """
    logger = get_run_logger()

    sr_duplicated = df["contract_id"].duplicated(keep=False)

    if not sr_duplicated.any():
        return df

    df["_quoted"] = (df["bid_size"].fillna(0) > 0) | (df["ask_size"].fillna(0) > 0)
    df["_traded"] = df["volume"].fillna(0) > 0
    df["_held"] = df["open_interest"].fillna(0) > 0

    df_conflicts = df[sr_duplicated].sort_values(
        ["_quoted", "_traded", "_held"], ascending=False
    )

    for contract_id, group in df_conflicts.groupby("contract_id"):
        logger.warning(
            "Resolving contract: %s (first row chosen):\n%s",
            contract_id,
            group.to_string(index=True),
        )

    df_conflicts_resolved = df_conflicts.drop_duplicates("contract_id", keep="first")
    df_result = pd.concat([df[~sr_duplicated], df_conflicts_resolved])

    return df_result.drop(columns=["_quoted", "_traded", "_held"]).reset_index(
        drop=True
    )


def find_invalid_rows(df: pd.DataFrame) -> pd.Series:
    """Find rows with impossible strikes, crossed quotes, or stale contracts.

    Contracts whose expiration precedes the snapshot date are considered stale.
    """
    logger = get_run_logger()

    sr_zero_strike = df["strike"] == 0
    sr_crossed = (df["bid"] > df["ask"]) & (df["bid"] > 0) & (df["ask"] > 0)
    sr_expired = df["expiration"] < df["date"]

    sr_invalid = sr_zero_strike | sr_crossed | sr_expired

    n_invalid = sr_invalid.sum()

    if n_invalid:
        logger.warning("Found %d invalid row(s)", n_invalid)

    return sr_invalid


def find_mismatched_rows(df: pd.DataFrame) -> pd.Series:
    """Find rows where the contract disagrees with the source's other columns.

    A cross-check for sources that return `strike`, `expiration`, `type` and `symbol`
    columns separately from the contract. Any disagreement is considered corruption.
    """
    logger = get_run_logger()

    df_parsed = parse_occ_tickers(df["contract_id"])

    sr_bad_symbol = df["symbol"] != df_parsed["underlying"]
    # The parsed expiration date will always be tz-naive.
    sr_bad_expiration = df["expiration"] != df_parsed["expiration"].dt.tz_localize(
        df["date"].dt.tz
    )
    sr_bad_type = df["type"] != df_parsed["type"]
    sr_bad_strike = pd.Series(
        df["strike"].to_numpy() != df_parsed["strike"].to_numpy(),
        index=df.index,
    )

    sr_mismatched = sr_bad_symbol | sr_bad_expiration | sr_bad_type | sr_bad_strike

    n_mismatched = sr_mismatched.sum()

    if n_mismatched:
        logger.warning("Found %d mismatched row(s)", n_mismatched)

    return sr_mismatched


def resolve_bad_rows(
    df: pd.DataFrame,
    sr_bad: pd.Series,
    bad_row_limit_fraction: float = 0.05,
) -> pd.DataFrame:
    """Drop rows considered corrupt.

    The day's data is considered invalid if the number of corrupt rows exceeds some
    threshold.
    """
    logger = get_run_logger()

    if not sr_bad.index.equals(df.index):
        raise ValueError("Indices do not align.")

    n_bad = sr_bad.sum()
    fraction = n_bad / len(df)

    if fraction > bad_row_limit_fraction:
        raise ValueError(f"Day considered invalid; bad rows {fraction:.2%} of day.")

    if n_bad:
        logger.warning("Dropping %d row(s) (%.2f%% of day).", n_bad, fraction * 100)

    return df.loc[~sr_bad].reset_index(drop=True)
