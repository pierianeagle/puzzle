import pandas as pd

from shared.data.returns import get_cumulative_returns


def get_drawdowns(returns: pd.Series) -> pd.Series:
    """Calculate the percentage draw downs of a series of percentage returns."""
    cumulative_returns = get_cumulative_returns(returns)
    net_asset_values = ((1 + cumulative_returns) * 100).fillna(100)
    high_water_marks = net_asset_values.cummax()
    drawdowns = net_asset_values / high_water_marks - 1

    return drawdowns


def split_drawdowns(drawdowns: pd.Series) -> list[pd.Series]:
    """Split a series of percentage draw downs by zeroes."""
    result = []
    current_drawdown = {}

    in_drawdown = False
    previous_key = None
    previous_value = None

    for key, value in drawdowns.items():
        # If the series is currently drawing down...
        if value < 0:
            # but we've only just started...
            if not in_drawdown:
                # then begin the new series with the preceding zero.
                current_drawdown = {previous_key: previous_value}

            current_drawdown[key] = value
            in_drawdown = True

        # If the series has recovered...
        elif in_drawdown:
            # then include the trailing zero and store the completed series.
            current_drawdown[key] = value
            result.append(pd.Series(current_drawdown))

            current_drawdown = {}
            in_drawdown = False

        previous_key, previous_value = key, value

    # If the series is still active...
    if in_drawdown:
        # then include the trailing zero and store the incomplete series.
        current_drawdown[previous_key] = previous_value
        result.append(pd.Series(current_drawdown))

    return result


def summarise_drawdowns(split_drawdowns: list[pd.Series]) -> pd.DataFrame:
    """Calculate the length and size of a list of series of percentage draw downs."""
    result = []

    for drawdown in split_drawdowns:
        valley_index = drawdown.idxmin()
        start_index = drawdown.index[0]
        end_index = drawdown.index[-1]

        result.append(
            pd.DataFrame(
                data={
                    "Start Index": [start_index],
                    "End Index": [end_index],
                    "Bottom Index": [valley_index],
                    "Decline": [drawdown.min()],
                    "Recovery": [((1 + drawdown.iloc[-1]) / (1 + drawdown.min())) - 1],
                    "Length": [end_index - start_index],
                    "Decline Length": [valley_index - start_index],
                    "Recovery Length": [end_index - valley_index],
                },
            )
        )

    return pd.concat(result).reset_index()
