from typing import Literal

import pandas as pd
from nautilus_trader.common.enums import LogColor
from nautilus_trader.model import (
    Bar,
    BarSpecification,
    BarType,
    Currency,
    InstrumentId,
    Venue,
)
from nautilus_trader.model.enums import AggregationSource

from jfdi.actors.equity import get_all_unrealised_pnls, get_equities, get_equity
from jfdi.extensions.strategies.weight import WeightStrategy, WeightStrategyConfig


class ShortFishyPairStrategyConfig(WeightStrategyConfig):
    instrument_ids: dict[Literal["long", "short"], InstrumentId]
    bar_spec: BarSpecification
    weight: float  # %
    bias: float  # %
    threshold: float  # %
    account_venue: Venue
    exchange_rate_venue: Venue
    reporting_currency: Currency
    order_id_tag: str  # 000


class ShortFishyPairStrategy(WeightStrategy):
    def __init__(self, config: ShortFishyPairStrategyConfig) -> None:
        """A strategy that ranks sectors by their momentum.

        This strategy assumes that the pair trades at the same venue, and keeps account
        and exchange rate venues separate to support Interactive Brokers.
        """
        super().__init__(config)

        self.instrument_venue = self.config.instrument_ids["long"].venue

        self.bar_types = {
            k: BarType(v, self.config.bar_spec, AggregationSource.EXTERNAL)
            for k, v in self.config.instrument_ids.items()
        }

        self.last_timestamps = {
            instrument_id: pd.NaT
            for instrument_id in self.config.instrument_ids.values()
        }

        self.previous_target_weights = {}

    def on_start(self) -> None:
        self.account = self.portfolio.account(self.config.account_venue)

        for bar_type in self.bar_types.values():
            self.subscribe_bars(bar_type)

    def on_stop(self) -> None:
        for position in self.cache.positions_open(strategy_id=self.id):
            self.close_all_positions(position.instrument_id)

        for bar_type in self.bar_types.values():
            self.unsubscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        instrument_id = bar.bar_type.instrument_id

        self.last_timestamps[instrument_id] = bar.ts_event

        if len(set(self.last_timestamps.values())) == 1:
            balances_total = self.account.balances_total()

            venues = {instrument.id.venue for instrument in self.cache.instruments()}

            unrealised_pnls = get_all_unrealised_pnls(self, venues)

            equities = get_equities(balances_total, unrealised_pnls)
            equity = get_equity(
                self,
                equities,
                self.config.exchange_rate_venue,
                self.config.reporting_currency,
            )

            if equity is None:
                self.log.warning("NO EXCHANGE RATES AVAILABLE.", LogColor.CYAN)
                return

            current_weights = self.get_current_weights(equity)

            if any(value is None for value in current_weights.values()):
                self.log.warning("NO EXCHANGE RATES AVAILABLE.", LogColor.CYAN)
                return

            target_weights = self.get_target_weights()
            order_weights = self.get_order_weights(current_weights, target_weights)

            order_weights = {
                k: v
                for k, v in order_weights.items()
                if abs(v) > self.config.weight * self.config.threshold
            }

            orders = self.create_orders(equity, order_weights)

            sorted_orders = sorted(orders, key=self.get_equity_released, reverse=True)

            for order in sorted_orders:
                self.submit_order(order)

            self.previous_target_weights = target_weights

    def get_target_weights(self) -> dict[InstrumentId, float]:
        """Calculate the portfolio's target weights (directional)."""
        target_weights = {
            instrument_id: -self.config.weight
            * (
                (1 / len(self.config.instrument_ids))
                + (1 if name == "long" else -1) * self.config.bias
            )
            for name, instrument_id in self.config.instrument_ids.items()
        }

        return target_weights
