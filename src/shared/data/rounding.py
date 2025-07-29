import numpy as np
import numpy.typing as npt
import pandas as pd


def ceil_with_precision(
    a: npt.NDArray | pd.Series, decimal_places: float = 0
) -> npt.NDArray | pd.Series:
    """Round numbers up to a number of decimal places.

    Args:
        a: An array of numbers.
        decimal_places: The number of decimal places to round up to.

    Returns:
        An array of floats rounded up.
    """
    return np.true_divide(np.ceil(a * 10**decimal_places), 10**decimal_places)


def floor_with_precision(
    a: npt.NDArray | pd.Series, decimal_places: float = 0
) -> npt.NDArray | pd.Series:
    """Round numbers down to a number of decimal places.

    Args:
        a: An array of numbers.
        decimal_places: The number of decimal places to round down to.

    Returns:
        An array of floats rounded down.
    """
    return np.true_divide(np.floor(a * 10**decimal_places), 10**decimal_places)


def round_directional(
    a: npt.NDArray | pd.Series, decimal_places: float = 0
) -> npt.NDArray | pd.Series:
    """Round a directional quantity down to a number of decimal places.

    Positive values (long orders) are rounded down whilst negative values
    (short orders) are rounded up, so that the absolute quantity is rounded down.

    Args:
        a: An array of numbers.
        decimal_places: The number of decimal places to round down to.

    Returns:
        An array of floats rounded down.
    """
    return np.where(
        a > 0,
        floor_with_precision(a, decimal_places),
        ceil_with_precision(a, decimal_places),
    )
