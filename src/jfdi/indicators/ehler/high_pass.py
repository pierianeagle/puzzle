import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType


class HighPass(Indicator):
    def __init__(
        self,
        period: int,
        price_type: PriceType = PriceType.LAST,
    ):
        """Ehler's high-pass filter.

        Args:
            period: Lookback.
            price_type: Price type to extract from ticks.
        """
        PyCondition.positive_int(period, "period")

        super().__init__(params=[period, price_type])

        self.short_name = "hp_f"

        self.period = period
        self.price_type = price_type

        self._prices = np.full(3, np.nan)
        self._high_pass = np.zeros(2)

        self._coefficients = compute_filter_coefficients(self.period)

    @property
    def value(self) -> float:
        if not self.initialized:
            return np.nan

        return self._high_pass[0]

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

        self._high_pass = self.update_high_pass(
            self._prices,
            self._high_pass,
            self._coefficients,
        )

    def _reset(self):
        self._prices[:] = np.nan
        self._high_pass[:] = 0.0


def compute_filter_coefficients(period):
    """Pre-compute the filter coefficients.

    These come from analog Butterworth filters, that're converted to digital recursive
    filters with the exponential term. If a bar is a sample, the highest frequency that
    you can reliably detect is 2 bars (the Nyquist frequency), but since financial data
    is extremely noisy, it's probably much higher than that. I'm guessing that it's
    about 5 bars (traditional bars do have multiple observations within them, but
    they're not sampled in time).
    """
    a1 = np.exp(-(2 ** (1 / 2)) * np.pi / period)

    c2 = 2 * a1 * np.cos(2 ** (1 / 2) * np.pi / period)
    c3 = -(a1**2)
    c1 = (1 + c2 - c3) / 4
    return c1, c2, c3


def update_high_pass(prices, previous_high_pass, coefficients):
    """Incrementally compute the high-pass filter."""
    c1, c2, c3 = coefficients

    high_pass = (
        c1 * (prices[0] - 2 * prices[1] + prices[2])
        + c2 * previous_high_pass[0]
        + c3 * previous_high_pass[1]
    )
    return np.array([high_pass, previous_high_pass[0]])
