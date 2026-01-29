import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType


class ALMA(Indicator):
    def __init__(
        self,
        period: int,
        offset: float = 0.85,
        sigma: float = 6.0,
        price_type: PriceType = PriceType.LAST,
    ):
        """The Arnaud Legoux Moving Average.

        As described in Legoux & Kouzis-Loukas. In Search of the Perfect Moving Average.
        Available at: https://www.forexfactory.com/attachment/file/1123528

        Args:
            period: Indicator lookback (greater than zero).
            offset: Position of the curve within the window.
            sigma: Controls the flatness of the weights curve.
            price_type: The price type to extract from quote ticks.

        Raises:
            ValueError: If `period` is not a positive integer.
        """
        PyCondition.positive_int(period, "period")

        super().__init__(params=[period, offset, sigma, price_type])

        self.period = period
        self.offset = offset
        self.sigma = sigma
        self.price_type = price_type

        self._prices = np.full(self.period, np.nan)

        self._weights = self._compute_weights(self.period, self.offset, self.sigma)

    @staticmethod
    def _compute_weights(period, offset, sigma):
        """Pre-compute the weights."""
        w = np.exp(
            -((np.arange(period) - int(np.floor(offset * (period - 1)))) ** 2)
            / (2 * (period / sigma) ** 2)
        )

        return w / np.sum(w)

    @property
    def value(self) -> float:
        """The current ALMA value."""
        if not self.initialized:
            return np.nan

        # Since I typically have the first index as the most recent entry, I need to
        # reverse the order of the weights.
        return np.dot(self._prices[::-1], self._weights)

    def handle_quote_tick(self, tick: QuoteTick):
        """Update the indicator with the given quote tick."""
        PyCondition.not_none(tick, "tick")

        self.update_raw(tick.extract_price(self.price_type).as_double())

    def handle_trade_tick(self, tick: TradeTick):
        """Update the indicator with the given trade tick."""
        PyCondition.not_none(tick, "tick")

        self.update_raw(tick.price.as_double())

    def handle_bar(self, bar: Bar):
        """Update the indicator with the given bar."""
        PyCondition.not_none(bar, "bar")

        self.update_raw(bar.close.as_double())

    def update_raw(self, value: float):
        """Update the indicator with the given raw value."""
        self._prices[1:] = self._prices[:-1]
        self._prices[0] = value

        if not self.initialized:
            self._set_has_inputs(True)

            if not np.isnan(self._prices).any():
                self._set_initialized(True)

    def _reset(self):
        """Reset stateful values in the class."""
        self._prices[:] = np.nan
