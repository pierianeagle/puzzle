from nautilus_trader.model import Bar, BarType, Quantity
from nautilus_trader.model.enums import OrderSide, PriceType
from nautilus_trader.trading.strategy import Strategy, StrategyConfig

from shared.data.rounding import floor_with_precision


class BuyAndHoldStrategyConfig(StrategyConfig):
    bar_type: BarType
    order_id_tag: str  # 000


class BuyAndHoldStrategy(Strategy):
    def __init__(self, config: BuyAndHoldStrategyConfig) -> None:
        super().__init__(config)

        self.instrument_id = self.config.bar_type.instrument_id
        self.first_bar = True

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.instrument_id)

        if self.instrument is None:
            self.log.error(
                f"Could not find instrument. instrument_id: {self.instrument_id}"
            )
            self.stop()
            return

        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if self.first_bar:
            account = self.portfolio.account(self.instrument_id.venue)
            balance = account.balances_total()[account.base_currency].as_double()

            # For some reason IB's TWS API doesn't support fractional trading,
            # even though the platform does.
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                # Rounding up creates a larger notional than the account's
                # balance, so I can't use `instrument.make_qty`.
                quantity=Quantity(
                    floor_with_precision(
                        balance / bar.close, self.instrument.size_precision
                    ),
                    self.instrument.size_precision,
                ),
            )
            self.submit_order(order)

        self.first_bar = False

    def on_stop(self) -> None:
        self.close_all_positions(self.instrument_id)
        self.unsubscribe_bars(self.config.bar_type)
