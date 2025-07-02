import pandas as pd


def purge_train_set(
    sr_vertical_barriers: pd.Series,
    sr_test_bounds: pd.Series,
) -> pd.Series:
    """Return train set samples that don't overlap with test set samples.

    This function purges (removes) training set samples whose information windows
    overlap with the testing set. Trades are typically structured with triple-barriers.
    If the vertical barrier (end time) of a training set sample overlaps with the
    testing set, then you're peeking at the future. See below for more information:

    López de Prado, M. (2018). Advances in Financial Machine Learning, Snippet 7.1,
    p.106. Wiley.

    Args:
        sr_vertical_barriers:
            A series (both sets) of vertical barriers, with a DatetimeIndex of
            start (prediction) times and a column of Timestamp end (closing) times (i.e,
            when the label becomes observable).
        sr_test_bounds:
            Testing set bounds of a similar structure, but for the entire dataset. If
            it's contiguous, then this series can be a single row.

    Returns:
        A series of training set samples of the same structure.
    """
    index_all_start_times = sr_vertical_barriers.index
    sr_all_end_times = sr_vertical_barriers

    mask_all_overlaps = pd.Series(index=sr_vertical_barriers.index, data=False)

    for test_start_time, test_end_time in sr_test_bounds.items():
        # If the train set sample starts within the test set, ends within the test set,
        # or envelops the test set.
        mask_current_overlaps = (index_all_start_times <= test_end_time) & (
            sr_all_end_times >= test_start_time
        )

        mask_all_overlaps |= mask_current_overlaps

    sr_train_vertical_barriers = sr_vertical_barriers[~mask_all_overlaps]

    return sr_train_vertical_barriers


def purge_train_set_vectorised(
    sr_vertical_barriers: pd.Series,
    sr_test_bounds: pd.Series,
) -> pd.Series:
    """A vectorised version of the above."""
    all_start_times = sr_vertical_barriers.index.values
    all_end_times = sr_vertical_barriers.values

    test_start_times = sr_test_bounds.index.values
    test_end_times = sr_test_bounds.values

    mask_overlaps = (all_start_times[:, None] <= test_end_times) & (
        all_end_times[:, None] >= test_start_times
    )

    return sr_vertical_barriers[~mask_overlaps.any(axis=1)]
