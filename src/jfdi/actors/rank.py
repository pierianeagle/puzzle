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
from nautilus_trader.model.enums import AggregationSource

from jfdi.extensions.indicators.ta_lib.manager import (
    TAFunctionWrapper,
    TALibIndicatorManager,
)

# Class variables can only be basic data types or instrument ids, so I'll create
# the rank data class during the backtest.
# @customdataclass
# class RankData(Data):
#     instrument_ids: np.ndarray = field(
#         default_factory=lambda: np.full(len(instruments), "", str)
#     )
#     ranks: np.ndarray = field(
#         default_factory=lambda: np.full(len(instruments), 0, int),
#     )


class RankActorConfig(ActorConfig):
    instrument_ids: list[InstrumentId]
    bar_spec: BarSpecification
    # indicator_class: Indicator
    # indicator_kwargs: dict
    indicator_class: str
    data_class: Data
    dtype_instrument_id: str
    dtype_rank: str
    component_id: ComponentId


class RankActor(Actor):
    def __init__(self, config: RankActorConfig) -> None:
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

        # Use NT's indicators.
        # self.indicators = {
        #     instrument_id: self.config.indicator_class(**self.config.indicator_kwargs)
        #     for instrument_id in self.config.instrument_ids
        # }
        # Use talib's indicators.
        self.indicator_managers = {}

        for instrument_id, bar_type in self.bar_types.items():
            self.indicator_managers[instrument_id] = TALibIndicatorManager(
                bar_type=bar_type,
                skip_uniform_price_bar=False,
                skip_zero_close_bar=False,
            )
            self.indicator_managers[instrument_id].set_indicators(
                [TAFunctionWrapper.from_str(self.config.indicator_class)]
            )

        self.last_timestamps = {
            instrument_id: pd.NaT for instrument_id in self.config.instrument_ids
        }

        self.ranks_key = f"{self.config.component_id}_RANKS"

    def on_start(self) -> None:
        for instrument_id, bar_type in self.bar_types.items():
            self.subscribe_bars(bar_type)

            self.register_indicator_for_bars(
                self.bar_types[instrument_id],
                # self.indicators[instrument_id],
                self.indicator_managers[instrument_id],
            )

    def on_stop(self) -> None:
        for bar_type in self.bar_types.values():
            self.unsubscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        if self.indicators_initialized():
            instrument_id = bar.bar_type.instrument_id

            self.last_timestamps[instrument_id] = bar.ts_event

            # Wait until every instrument's data has arrived.
            if len(set(self.last_timestamps.values())) == 1:
                values = {
                    # instrument_id: self.indicators[instrument_id].value
                    instrument_id: self.indicator_managers[instrument_id].value(
                        self.config.indicator_class
                    )
                    for instrument_id in self.config.instrument_ids
                }

                ranks = {
                    instrument_id: rank
                    for rank, (instrument_id, _) in enumerate(
                        sorted(values.items(), key=lambda item: item[1], reverse=True),
                        start=1,
                    )
                }

                rank_data = self.config.data_class(
                    ts_event=bar.ts_event,
                    ts_init=bar.ts_init,
                    instrument_ids=np.array(
                        list(ranks.keys()),
                        dtype=np.dtype(self.config.dtype_instrument_id),
                    ),
                    ranks=np.array(
                        list(ranks.values()),
                        dtype=np.dtype(self.config.dtype_rank),
                    ),
                )

                self.publish_data(
                    DataType(
                        self.config.data_class,
                        metadata={
                            "bar_spec": self.config.bar_spec,
                            # "indicator_class": self.config.indicator_class.__name__,
                            # "indicator_kwargs": self.config.indicator_kwargs,
                            "indicator_class": self.config.indicator_class,
                            "dtype_instrument_id": self.config.dtype_instrument_id,
                            "dtype_rank": self.config.dtype_rank,
                        },
                    ),
                    rank_data,
                )
