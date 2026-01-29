import numpy as np
import pandas as pd
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import (
    Bar,
    BarSpecification,
    BarType,
    ComponentId,
    DataType,
    InstrumentId,
)
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.enums import AggregationSource
from scipy.spatial import distance
from sklearn.covariance import LedoitWolf


@customdataclass
class TurbulenceData(Data):
    turbulence: float = 0


class TurbulenceActorConfig(ActorConfig):
    instrument_ids: list[InstrumentId]
    bar_spec: BarSpecification
    fast_period: int
    slow_period: int
    component_id: ComponentId


class TurbulenceActor(Actor):
    def __init__(self, config: TurbulenceActorConfig) -> None:
        """Publish the ranks of a series of instruments."""
        super().__init__(config)

        self.bar_types = {
            instrument_id: BarType(
                instrument_id,
                self.config.bar_spec,
                AggregationSource.EXTERNAL,
                # AggregationSource.INTERNAL,
            )
            for instrument_id in self.config.instrument_ids
        }

        self.last_closes = {
            instrument_id: np.nan for instrument_id in self.config.instrument_ids
        }

        self.last_timestamps = {
            instrument_id: pd.NaT for instrument_id in self.config.instrument_ids
        }

        self.returns = {
            instrument_id: np.full(self.config.slow_period, np.nan)
            for instrument_id in self.config.instrument_ids
        }

        self.turbulence_key = f"{self.config.component_id}_TURBULENCE"

    def on_start(self) -> None:
        for bar_type in self.bar_types.values():
            self.subscribe_bars(bar_type)

    def on_stop(self) -> None:
        for bar_type in self.bar_types.values():
            self.unsubscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        instrument_id = bar.bar_type.instrument_id

        if self.last_closes[instrument_id]:
            self.returns[instrument_id][1:] = self.returns[instrument_id][:-1]
            self.returns[instrument_id][0] = (
                bar.close  # np.log(bar.close.as_double())
                - self.last_closes[instrument_id]
            ) / self.last_closes[instrument_id]

        self.last_closes[instrument_id] = bar.close  # np.log(bar.close.as_double())
        self.last_timestamps[instrument_id] = bar.ts_event

        # Wait until every instrument's data has arrived.
        if all(not np.isnan(arr).any() for arr in self.returns.values()):
            if len(set(self.last_timestamps.values())) == 1:
                # The data's been transposed to ensure it has shape:
                # (self.config.slow_period, len(self.config.instrument_ids))
                matrix_returns = np.vstack(list(self.returns.values()))

                # In order to calculate the cumulative return I need to reverse the
                # lastest returns (of length `fast_period``) before taking the geometric
                # product.
                # r = matrix_returns[:, 0]
                r = (
                    np.prod(
                        1 + matrix_returns[:, : self.config.fast_period][:, ::-1],
                        axis=1,
                    )
                    - 1
                )

                # The mean return is calculated over the whole matrix (of length
                # `slow_period`).
                # mu = np.mean(matrix_returns, axis=1)
                mu = np.median(matrix_returns, axis=1)

                # sigma = np.cov(matrix_returns)
                sigma = LedoitWolf().fit(matrix_returns.T).covariance_

                sigma_inv = np.linalg.inv(sigma)

                # Where the result must be scaled down by the `fast_period`.
                turbulence = (
                    1 / (len(self.config.instrument_ids) * self.config.fast_period)
                ) * distance.mahalanobis(r, mu, sigma_inv) ** 2

                turbulence_data = TurbulenceData(
                    ts_event=bar.ts_event,
                    ts_init=bar.ts_init,
                    turbulence=turbulence,
                )

                self.publish_data(
                    DataType(
                        TurbulenceData,
                        metadata={
                            # "instrument_ids": self.config.instrument_ids,
                            "bar_spec": self.config.bar_spec,
                            "fast_period": self.config.fast_period,
                            "slow_period": self.config.slow_period,
                        },
                    ),
                    turbulence_data,
                )
