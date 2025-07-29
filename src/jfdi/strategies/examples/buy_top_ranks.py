import numpy as np
from nautilus_trader.core.data import Data
from nautilus_trader.model import DataType, InstrumentId
from nautilus_trader.trading.strategy import StrategyConfig

from jfdi.extensions.strategies.weight import WeightStrategy


class BuyTopRanksStrategyConfig(StrategyConfig):
    instrument_ids: list[InstrumentId]
    data_class: Data
    top: int  # rank threshold
    # bottom: int  # rank threshold
    weight: float  # %
    threshold: float  # % (for rebalancing)
    order_id_tag: str  # 000


class BuyTopRanksStrategy(WeightStrategy):
    def __init__(self, config: BuyTopRanksStrategyConfig) -> None:
        """A strategy that ranks sectors by their momentum."""
        super().__init__(config)

    def on_start(self) -> None:
        self.subscribe_data(DataType(self.config.data_class))

        # The set should be traded using the same NT account (and so, be at
        # the same venue).
        self.venue = self.config.instrument_ids[0].venue
        self.account = self.portfolio.account(self.venue)

        self.previous_target_weights = {}

    def on_stop(self) -> None:
        for position in self.cache.positions_open(strategy_id=self.id):
            self.close_all_positions(position.instrument_id)

        self.unsubscribe_data(DataType(self.config.data_class))

    def on_data(self, data: Data) -> None:
        if isinstance(data, self.config.data_class):
            equities = self.get_equities()

            current_weights = self.get_current_weights(equities)
            target_weights = self.get_target_weights(data)
            order_weights = self.get_order_weights(current_weights, target_weights)

            # Only change the portfolio when an instrument has knocked another
            # off the throne. Don't rebalance it on every data release.
            order_weights = {
                k: v for k, v in order_weights.items() if abs(v) > self.config.threshold
            }

            # equity = self.get_equity(equities)
            equity = equities[self.account.base_currency]

            orders = self.create_orders(equity, order_weights)

            sorted_orders = sorted(orders, key=self.get_equity_released, reverse=True)

            for order in sorted_orders:
                self.submit_order(order)

            self.previous_target_weights = target_weights

    def get_target_weights(
        self,
        data: Data,
    ) -> dict[InstrumentId, float]:
        """Calculate the portfolio's target weights (directional)."""
        top_instrument_ids = data.instrument_ids[
            np.argsort(data.ranks)[: self.config.top]
        ]

        # Where you first have to type-cast from `np.str_` to `str`.
        top_instrument_ids = np.vectorize(lambda x: InstrumentId.from_str(str(x)))(
            top_instrument_ids
        )

        target_weights = {
            instrument_id: self.config.weight
            * (1.0 / self.config.top)
            * float(
                self.account.leverages().get(
                    instrument_id, self.account.default_leverage
                )
            )
            for instrument_id in top_instrument_ids
        }

        return target_weights
