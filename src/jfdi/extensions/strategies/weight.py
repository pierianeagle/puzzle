from nautilus_trader.model import InstrumentId, Money, Quantity
from nautilus_trader.model.enums import OrderSide, PriceType
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.orders.base import Order
from nautilus_trader.trading.strategy import Strategy, StrategyConfig

from shared.data.rounding import round_directional


class WeightStrategy(Strategy):
    def __init__(self, config: StrategyConfig) -> None:
        """A strategy wrapper that adds support for target weights.

        This strategy does not support multi-currency accounts.
        """
        super().__init__(config)

    def get_equities(self) -> dict[Currency, float]:
        """Calculate the portfolio's equity in a given currency."""
        balances_total = self.account.balances_total()
        unrealised_pnls = self.portfolio.unrealized_pnls(self.venue)

        currencies_union = balances_total.keys() | unrealised_pnls.keys()

        equities = {
            currency: balances_total.get(
                currency, Money(0, currency=currency)
            ).as_double()
            # Unrealised pnls are reported in the settlement currency.
            + unrealised_pnls.get(currency, Money(0, currency=currency)).as_double()
            for currency in currencies_union
        }

        return equities

    def get_current_weights(
        self,
        # equity: float,
        equities: dict[Currency, float],
    ) -> dict[InstrumentId, float]:
        """Calculate the the portolfio's current weights (directional)."""
        current_weights = {
            position.instrument_id: (
                # If the portfolio is short multiply the allocation by -1.
                (self.portfolio.is_net_long(position.instrument_id) * 2 - 1)
                * self.portfolio.net_exposure(position.instrument_id).as_double()
                / equities[self.account.base_currency]
            )
            for position in self.cache.positions_open(strategy_id=self.id)
        }

        return current_weights

    def get_target_weights(self) -> dict[InstrumentId, float]:
        """Calculate the portfolio's target weights (directional).

        Overload me!
        """
        return {}

    def get_order_weights(
        self,
        current_weights: dict[InstrumentId, float],
        target_weights: dict[InstrumentId, float],
    ) -> dict[InstrumentId, float]:
        """Calculate the order sizes in portfolio weights."""
        instrument_ids_union = current_weights.keys() | target_weights.keys()

        order_weights = {
            instrument_id: target_weights.get(instrument_id, 0.0)
            - current_weights.get(instrument_id, 0.0)
            for instrument_id in instrument_ids_union
        }

        # Order quantities of zero are nonsense.
        order_weights = {k: v for k, v in order_weights.items() if v != 0}

        return order_weights

    def create_orders(
        self,
        equity: float,
        order_weights: dict[InstrumentId, float],
    ) -> list[Order]:
        """Get the (market) orders from the supplied weight differences."""
        orders = []

        for instrument_id, order_weight in order_weights.items():
            instrument = self.cache.instrument(instrument_id)
            last_price = self.cache.price(instrument_id, PriceType.LAST)

            order_quantity = Quantity(
                round_directional(
                    equity * abs(order_weight) / last_price,
                    instrument.size_precision,
                ),
                instrument.size_precision,
            )

            # Sometimes the prices of these instruments get so high that you
            # can't make a trade if you're not trading fractional shares.
            if order_quantity != 0:
                orders.append(
                    self.order_factory.market(
                        instrument_id=instrument_id,
                        order_side=(
                            OrderSide.BUY if order_weight > 0 else OrderSide.SELL
                        ),
                        # Rounding up can create a larger notional than the
                        # account balance, so I can't use `instrument.make_qty`.
                        quantity=order_quantity,
                    )
                )

        return orders

    def get_equity_released(self, order: Order) -> float:
        """Sort market orders to free up equity before trying to spend it."""
        # Buy orders take equity unless the portfolio is net short that position.
        return (
            1
            if not self.portfolio.net_position(order.instrument_id)
            else (self.portfolio.is_net_long(order.instrument_id) * 2 - 1)
            * (-1 if order.side == OrderSide.BUY else 1)
            * self.cache.price(order.instrument_id, PriceType.LAST)
            * order.quantity
        )
