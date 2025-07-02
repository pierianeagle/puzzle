from collections.abc import Generator

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.model_selection import KFold

from jfmi.cross_validation.purge import purge_train_set


class PurgedKFold(KFold):
    """A scikit-learn purged cross-validator for time-series.

    This class splits the dataset, and purges (removes) training set samples whose
    information windows overlap with the testing set. See below for more information:

    López de Prado, M. (2018). Advances in Financial Machine Learning, Chapter 7. Wiley.

    Args:
        sr_vertical_barriers:
            A series (both sets) of vertical barriers, with a DatetimeIndex of
            start (prediction) times and a column of Timestamp end (closing) times (i.e,
            when the label becomes observable).
        n_splits:
            The number of folds, which must be greater than 1.
        pct_embargo: A percentage embargo size.
    """

    def __init__(
        self,
        sr_vertical_barriers: pd.Series,
        n_splits: int = 5,
        pct_embargo: float = 0.0,
    ):
        super().__init__(n_splits, shuffle=False, random_state=None)

        self.sr_vertical_barriers = sr_vertical_barriers
        self.pct_embargo = pct_embargo

    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series = None,
        groups: pd.Series = None,
    ) -> Generator[tuple[npt.NDArray, npt.NDArray]]:
        """Generate indices to split data into training and testing sets.

        Args:
            X:
                Training data of shape (n_samples, n_features), where the number of
                samples is the same as in sr_vertical_barriers.
            y:
                Target data of shape (n_samples,), for supervised learning. Always
                ignored, exists for compatibility.
            groups:
                Group labels for the samples used while splitting the dataset into
                train/test sets. Always ignored, exists for compatibility.

        Yields:
            Tuples of shape (train_indices, test_indices).
        """
        if X.shape[0] != self.sr_vertical_barriers.shape[0]:
            raise ValueError(
                "`X` and `sr_vertical_barriers` must be of the same length."
            )

        indices = np.arange(X.shape[0])

        # The test set bounds walk forwards without overlapping.
        test_bounds_indices = [
            (split_indices[0], split_indices[-1] + 1)
            for split_indices in np.array_split(indices, self.n_splits)
        ]

        for start_index, end_index in test_bounds_indices:
            # Parition the test set indices first.
            test_indices = indices[start_index:end_index]

            # Optionally, embargo samples after the end of the test set.
            if end_index < X.shape[0]:
                end_index += int(X.shape[0] * self.pct_embargo)

            # The calculation can be accelerated if the bounds are contiguous.
            # sr_test_bounds_times = self.sr_vertical_barriers.iloc[
            #     start_index:end_index
            # ]
            # The test set covers this area.
            sr_test_bounds_times = pd.Series(
                index=[self.sr_vertical_barriers.index[start_index]],
                data=[self.sr_vertical_barriers.iloc[end_index - 1]],
            )

            # Purge overlapping train set samples.
            sr_train_times = purge_train_set(
                self.sr_vertical_barriers, sr_test_bounds_times
            )

            train_indices = self.sr_vertical_barriers.index.get_indexer(
                sr_train_times.index
            )

            yield train_indices, test_indices
