import numpy as np
import pandas as pd
from prefect import get_run_logger

from jfri.contracts.occ import parse_occ_tickers


def resolve_duplicate_contracts(df: pd.DataFrame) -> pd.DataFrame:
    """Pick the highest-quality row per contract when duplicates are emitted.

    These rows are assumed to have (in descending priority): non-zero quote sizes,
    non-zero volume, non-zero open interest, the tightest relative spread, the largest
    size, the largest volume, then the largest open interest. The mark is used as a
    tie-breaker.
    """
    logger = get_run_logger()

    sr_duplicated = df["option"].duplicated(keep=False)

    if not sr_duplicated.any():
        return df

    bid = df["bid"].fillna(0)
    ask = df["ask"].fillna(0)
    mid = (bid + ask) / 2
    bid_size = df["bid_size"].fillna(0)
    ask_size = df["ask_size"].fillna(0)
    volume = df["volume"].fillna(0)
    open_interest = df["open_interest"].fillna(0)

    two_sided = (bid > 0) & (ask > 0)

    df["_quoted"] = (bid_size > 0) | (ask_size > 0)
    df["_traded"] = volume > 0
    df["_held"] = open_interest > 0
    df["_relative_spread"] = np.where(
        two_sided, (ask - bid) / np.maximum(mid, 0.25), np.inf
    )
    df["_size"] = bid_size + ask_size

    df_conflicts = df[sr_duplicated].sort_values(
        by=[
            "_quoted",
            "_traded",
            "_held",
            "_relative_spread",
            "_size",
            "volume",
            "open_interest",
            "mark",
        ],
        ascending=[False, False, False, True, False, False, False, False],
    )

    for option, group in df_conflicts.groupby("option"):
        logger.warning(
            "Resolving contract: %s (first row chosen):\n%s",
            option,
            group.to_string(index=True),
        )

    df_conflicts_resolved = df_conflicts.drop_duplicates("option", keep="first")
    df_result = pd.concat([df[~sr_duplicated], df_conflicts_resolved])

    return df_result.drop(
        columns=["_quoted", "_traded", "_held", "_relative_spread", "_size"]
    ).reset_index(drop=True)


def find_invalid_rows(df: pd.DataFrame) -> pd.Series:
    """Find rows with impossible strikes, crossed quotes, or stale contracts.

    Contracts whose expiration precedes the snapshot date are considered stale.
    """
    logger = get_run_logger()

    sr_zero_strike = df["strike"] == 0
    sr_crossed = (df["bid"] > df["ask"]) & (df["bid"] > 0) & (df["ask"] > 0)
    sr_expired = df["expiration"] < df["date"]

    if sr_zero_strike.any():
        logger.warning("Found %d row(s) with zero strikes.", sr_zero_strike.sum())
    if sr_crossed.any():
        logger.warning("Found %d row(s) with crossed quotes.", sr_crossed.sum())
    if sr_expired.any():
        logger.warning("Found %d row(s) with expired contracts.", sr_expired.sum())

    sr_invalid = sr_zero_strike | sr_crossed | sr_expired

    return sr_invalid


def find_mismatched_rows(df: pd.DataFrame) -> pd.Series:
    """Find rows where the contract disagrees with the source's other columns.

    A cross-check for sources that return `strike`, `expiration`, `type` and `symbol`
    columns separately from the contract. Any disagreement is considered corruption.
    """
    logger = get_run_logger()

    df_parsed = parse_occ_tickers(df["option"])

    sr_mismatched_symbol = df["symbol"] != df_parsed["underlying"]
    # The parsed expiration date will always be tz-naive.
    sr_mismatched_expiration = df["expiration"] != df_parsed[
        "expiration"
    ].dt.tz_localize(df["date"].dt.tz)
    sr_mismatched_type = df["type"] != df_parsed["type"]
    sr_mismatched_strike = pd.Series(
        ~np.isclose(df["strike"], df_parsed["strike"], rtol=0, atol=1e-6),
        index=df.index,
    )

    if sr_mismatched_symbol.any():
        logger.warning(
            "Found %d row(s) with mismatched symbols.", sr_mismatched_symbol.sum()
        )
    if sr_mismatched_expiration.any():
        logger.warning(
            "Found %d row(s) with mismatched expirations.",
            sr_mismatched_expiration.sum(),
        )
    if sr_mismatched_type.any():
        logger.warning(
            "Found %d row(s) with mismatched types.", sr_mismatched_type.sum()
        )
    if sr_mismatched_strike.any():
        logger.warning(
            "Found %d row(s) with mismatched strikes.", sr_mismatched_strike.sum()
        )

    sr_mismatched = (
        sr_mismatched_symbol
        | sr_mismatched_expiration
        | sr_mismatched_type
        | sr_mismatched_strike
    )

    return sr_mismatched


def find_low_quality_rows(
    df: pd.DataFrame,
    max_relative_spread: float = 0.75,
    min_bid: float = 0.05,
) -> pd.Series:
    """Find rows whose quote is unusable for pricing.

    This includes rows that don't have two-sided markets and have no open interest
    and no volume, have tiny bids which are quote-noise, and have wide spreads.
    One-sided markets are not excluded here.
    """
    logger = get_run_logger()

    bid = df["bid"].fillna(0)
    ask = df["ask"].fillna(0)
    mid = (bid + ask) / 2
    volume = df["volume"].fillna(0)
    open_interest = df["open_interest"].fillna(0)

    two_sided = (bid > 0) & (ask > 0)
    relative_spread = np.where(two_sided, (ask - bid) / np.maximum(mid, 0.25), np.inf)

    sr_truly_empty = (bid == 0) & (ask == 0) & (open_interest == 0) & (volume == 0)
    sr_tiny_bid = (bid > 0) & (bid < min_bid)
    sr_wide_spread = pd.Series(
        two_sided & (relative_spread > max_relative_spread), index=df.index
    )

    sr_low_quality = sr_truly_empty | sr_tiny_bid | sr_wide_spread

    if sr_truly_empty.any():
        logger.warning("Found %d row(s) that're empty.", sr_truly_empty.sum())
    if sr_tiny_bid.any():
        logger.warning(
            "Found %d row(s) with tiny bids (bid < %.2f)",
            sr_tiny_bid.sum(),
            min_bid,
        )
    if sr_wide_spread.any():
        logger.warning(
            "Found %d row(s) with wide spreads (relative_spread > %.2f)",
            sr_wide_spread.sum(),
            max_relative_spread,
        )

    return sr_low_quality


# TODO - Add risk-free rates and dividend yields.
def find_arbitrage_violations(
    df: pd.DataFrame,
    spot: float,
    tolerance: float = 0.02,
) -> pd.Series:
    """Find rows that breach the rate-free upper no-arbitrage bounds.

    The two valid no-arbitrage bounds for option pricing are an intrinsic floor and a
    pricing ceiling. They behave differently across exercise styles:
    - Floor (intentionally omitted here):
        - American (single-name US equity options): `C >= max(S - K, 0)` and
            `P >= max(K - S, 0)` hold strictly because the option can be exercised for
            intrinsic value at any time.
        - European (cash-settled index options): the floor is `C >= max(S*e^(-qT) -
            K*e^(-rT), 0)`, which when `r > q` is below `max(S - K, 0)`. Deep-ITM
            European calls routinely trade slightly below undiscounted intrinsic.
            Applying the American floor here produces large false-positive cohorts, so
            it has been omitted.
    - Ceiling (checked here): `C <= S` and `P <= K` hold for both styles and under any
        non-negative `r` and `q`. The European discounted ceilings `C <= S*e^(-qT)` and
        `P <= K*e^(-rT)` are tighter, so the undiscounted version is the loosest valid
        upper bound and applies universally. A call quoted above spot or a put quoted
        above strike must be an error.

    A tolerance ensures rounding and minor staleness doesn't produce false positives.
    """
    logger = get_run_logger()

    bid = df["bid"].fillna(0)
    ask = df["ask"].fillna(0)
    two_sided = (bid > 0) & (ask > 0)
    mid = (bid + ask) / 2
    strike = df["strike"]
    is_call = df["type"] == "call"

    above_call_ceiling = is_call & (mid > spot + tolerance)
    above_put_ceiling = (~is_call) & (mid > strike + tolerance)

    sr_violation = two_sided & (above_call_ceiling | above_put_ceiling)

    if sr_violation.any():
        logger.warning(
            "Found %d arb-violating row(s) at spot=%.4f", int(sr_violation.sum()), spot
        )

    return sr_violation


def resolve_bad_rows(
    df: pd.DataFrame,
    sr_bad: pd.Series,
    bad_row_limit_fraction: float = 0.20,
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
