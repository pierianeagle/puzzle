import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType

from jfdi.indicators.ehler.high_pass import compute_filter_coefficients


class LowPass(Indicator):
    def __init__(
        self,
        period: int,
        price_type: PriceType = PriceType.LAST,
    ):
        """Ehler's low-pass filter.

        Args:
            period: Lookback.
            price_type: Price type to extract from ticks.
        """
        PyCondition.positive_int(period, "period")

        super().__init__(params=[period, price_type])

        self.short_name = "bp_f"

        self.period = period
        self.price_type = price_type

        self._prices = np.full(3, np.nan)
        self._low_pass = np.zeros(2)

        self._coefficients = compute_filter_coefficients(self.period)

    @property
    def value(self) -> float:
        if not self.initialized:
            return np.nan

        return self._low_pass[0]

    def handle_quote_tick(self, tick: QuoteTick):
        PyCondition.not_none(tick, "tick")

        self.update_raw(tick.extract_price(self.price_type).as_double())

    def handle_trade_tick(self, tick: TradeTick):
        PyCondition.not_none(tick, "tick")

        self.update_raw(tick.price.as_double())

    def handle_bar(self, bar: Bar):
        PyCondition.not_none(bar, "bar")

        self.update_raw(bar.close.as_double())

    def update_raw(self, value: float):
        self._prices[1:] = self._prices[:-1]
        self._prices[0] = value

        if not self.initialized:
            self._set_has_inputs(True)

            if not np.isnan(self._prices).any():
                self._set_initialized(True)

        self._low_pass = update_low_pass(
            self._prices,
            self._low_pass,
            self._coefficients,
        )

    def _reset(self):
        self._prices[:] = np.nan
        self._low_pass[:] = 0.0


def update_low_pass(prices, previous_low_pass, coefficients):
    """Incrementally compute the low-pass filter."""
    c1, c2, c3 = coefficients

    low_pass = (
        (1 - c1) * prices[0]
        + (2 * c1 - c2) * prices[1]
        - (c1 + c3) * prices[2]
        + c2 * previous_low_pass[0]
        + c3 * previous_low_pass[1]
    )
    return np.array([low_pass, previous_low_pass[0]])
