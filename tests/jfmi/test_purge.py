import pandas as pd
import pytest

from jfmi.cross_validation.purge import purge_train_set


@pytest.fixture
def vertical_barriers():
    start_times = pd.to_datetime(
        [
            "2023-01-01",
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
            "2023-01-06",
            "2023-01-07",
            "2023-01-08",
            "2023-01-09",
            "2023-01-10",
        ]
    )
    end_times = pd.to_datetime(
        [
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
            "2023-01-06",
            "2023-01-07",
            "2023-01-08",
            "2023-01-09",
            "2023-01-10",
            "2023-01-11",
        ]
    )
    return pd.Series(index=start_times, data=end_times)


@pytest.fixture
def contiguous_test_set_bounds():
    return pd.Series(
        index=[
            pd.Timestamp("2023-01-03"),
        ],
        data=[
            pd.Timestamp("2023-01-09"),
        ],
    )


@pytest.fixture
def non_contiguous_test_set_bounds():
    return pd.Series(
        index=[
            pd.Timestamp("2023-01-03"),
            pd.Timestamp("2023-01-08"),
        ],
        data=[
            pd.Timestamp("2023-01-05"),
            pd.Timestamp("2023-01-09"),
        ],
    )


def test_purge_train_set_contiguous(vertical_barriers, contiguous_test_set_bounds):
    result = purge_train_set(vertical_barriers, contiguous_test_set_bounds)

    expected = pd.Series(
        index=pd.to_datetime(
            [
                "2023-01-01",
                "2023-01-10",
            ]
        ),
        data=pd.to_datetime(
            [
                "2023-01-02",
                "2023-01-11",
            ]
        ),
    )

    pd.testing.assert_series_equal(result.sort_index(), expected.sort_index())


def test_purge_train_set_non_contiguous(
    vertical_barriers, non_contiguous_test_set_bounds
):
    result = purge_train_set(vertical_barriers, non_contiguous_test_set_bounds)

    expected = pd.Series(
        index=pd.to_datetime(
            [
                "2023-01-01",
                "2023-01-06",
                "2023-01-10",
            ]
        ),
        data=pd.to_datetime(
            [
                "2023-01-02",
                "2023-01-07",
                "2023-01-11",
            ]
        ),
    )

    pd.testing.assert_series_equal(result.sort_index(), expected.sort_index())
