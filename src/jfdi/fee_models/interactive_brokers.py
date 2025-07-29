from nautilus_trader.backtest.models import FeeModel
from nautilus_trader.model import Currency, Money, Price, Quantity
from nautilus_trader.model.instruments import (
    Equity,
    FuturesContract,
    Instrument,
    OptionContract,
)
from nautilus_trader.model.orders import Order


class InteractiveBrokersFeeModel(FeeModel):
    def __init__(self) -> None:
        """Interactive Brokers Pro Fixed custom fee model (USD)."""
        super().__init__()

        self.share_commission = 0.005  # USD
        self.minimum_fee_per_order = 1.000  # USD
        self.maximum_fee_percent_per_order = 0.01  # %

    def get_commission(
        self,
        order: Order,
        fill_qty: Quantity,
        fill_px: Price,
        instrument: Instrument,
    ) -> Money:
        # fill_qty = float(order.quantity)

        match instrument:
            case Equity():
                # "In the event the calculated maximum per order is less than
                # the minimum per order, the maximum per order will be
                # assessed."
                commission = min(
                    max(
                        self.minimum_fee_per_order,  # min of $1
                        self.share_commission
                        * fill_qty.as_double(),  # $0.005 per share
                    ),
                    self.maximum_fee_percent_per_order
                    * fill_qty.as_double()
                    * fill_px.as_double(),  # max of 1%
                )

            # TODO - Implement futures contract fee model.
            case FuturesContract():
                commission = 0

            # TODO - Implement options contract fee model.
            case OptionContract():
                commission = 0

            case _:
                commission = 0

        return Money(commission, Currency.from_str("USD"))
