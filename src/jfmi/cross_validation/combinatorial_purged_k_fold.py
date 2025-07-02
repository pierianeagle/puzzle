from collections.abc import Generator
from itertools import combinations

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy.special import comb
from sklearn.model_selection import KFold

from jfmi.cross_validation.purge import purge_train_set


class CombinatorialPurgedKFold(KFold):
    """A scikit-learn combinatorial purged cross-validator for time-series.

    This class combinatorially splits the dataset, creates multiple complete backtest
    paths from it, and purges (removes) training set samples whose information windows
    overlap with the testing set. The backtest paths are populated as split yields
    indices. See below for more information:

    López de Prado, M. (2018). Advances in Financial Machine Learning, Chapter 12.
    Wiley.

    Args:
        sr_vertical_barriers:
            A series (both sets) of vertical barriers, with a DatetimeIndex of
            start (prediction) times and a column of Timestamp end (closing) times (i.e,
            when the label becomes observable).
        n_folds:
            The number of train set splits, which must be greater than 1.
        n_test_folds:
            The number of test set splits, which must be greater than 1.
        pct_embargo: A percentage embargo to apply after each test set.
    """

    def __init__(
        self,
        sr_vertical_barriers: pd.Series,
        n_folds: int = 6,
        n_test_folds: int = 2,
        pct_embargo: float = 0.0,
    ):
        self.sr_vertical_barriers = sr_vertical_barriers
        self.pct_embargo = pct_embargo
        self.n_folds = n_folds
        self.n_test_folds = n_test_folds
        self.backtest_paths = {0: []}

    @property
    def n_splits(self):
        """The number of splits."""
        return comb(self.n_folds, self.n_test_folds)

    @property
    def n_backtest_paths(self):
        """The number of backtest paths."""
        return self.n_splits * self.n_test_folds // self.n_folds

    @property
    def backtest_paths_populated(self):
        """Whether the backtest paths have been fully populated."""
        return len(self.backtest_paths) == self.n_backtest_paths and all(
            len(path) == self.n_folds for path in self.backtest_paths.values()
        )

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

        test_bounds_indices = [
            (split_indices[0], split_indices[-1] + 1)
            for split_indices in np.array_split(indices, self.n_folds)
        ]

        # This time, find the 2-element combinations of the k-fold splits.
        combinatorial_test_bounds_indices = list(
            combinations(
                zip(np.arange(self.n_folds), test_bounds_indices, strict=False),
                self.n_test_folds,
            )
        )

        for split, combination in enumerate(combinatorial_test_bounds_indices):
            test_indices = []
            test_bounds_times_srs = []

            for fold, (start_index, end_index) in combination:
                test_indices.append(indices[start_index:end_index])

                # Greedily store test set folds in the first backtest path that doesn't
                # contain them.
                if not self.backtest_paths_populated:
                    entry = {
                        "split": split,
                        "fold": fold,
                        "start_index": start_index,
                        "end_index": end_index - 1,
                    }

                    for backtest, segments in self.backtest_paths.items():
                        if any(segment.get("fold") == fold for segment in segments):
                            continue
                        else:
                            self.backtest_paths[backtest].append(entry)
                            break
                    else:
                        self.backtest_paths[max(self.backtest_paths) + 1] = [entry]

                if end_index < X.shape[0]:
                    end_index += int(X.shape[0] * self.pct_embargo)

                test_bounds_times_srs.append(
                    pd.Series(
                        index=[self.sr_vertical_barriers.index[start_index]],
                        data=[self.sr_vertical_barriers.iloc[end_index - 1]],
                    )
                )

            test_indices = np.concatenate(test_indices)
            sr_test_bounds_times = pd.concat(test_bounds_times_srs)

            sr_train_times = purge_train_set(
                self.sr_vertical_barriers, sr_test_bounds_times
            )

            train_indices = self.sr_vertical_barriers.index.get_indexer(
                sr_train_times.index
            )

            yield np.array(train_indices), np.array(test_indices)
