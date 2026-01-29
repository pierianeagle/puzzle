import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType


class MMI(Indicator):
    def __init__(
        self,
        period: int,
        price_type: PriceType = PriceType.LAST,
    ):
        """The Market Meanness Index.

        The market meanness measures how often price movements revert toward the median.
        Independent and identically distributed series revert to the median 75% of the
        time. Lower values indicate stronger trending behavior, whilst higher values
        indicate either mean-reverting or random conditions.

        Args:
            period: Indicator lookback (greater than zero).
            price_type: The price type to extract from quote ticks.

        Raises:
            ValueError: If `period` is not a positive integer.
        """
        PyCondition.positive_int(period, "period")

        super().__init__(params=[period, price_type])

        self.period = period
        self.price_type = price_type

        self._prices = np.full(self.period, np.nan)
        self.median = np.nan

    @property
    def value(self) -> float:
        """The current market meanness."""
        if not self.initialized:
            return np.nan

        prev = self._prices[1:]
        curr = self._prices[:-1]

        # The number of lower and higher reversions that were avoided.
        number_higher = np.sum((curr > self.median) & (curr > prev))
        number_lower = np.sum((curr < self.median) & (curr < prev))

        return (number_higher + number_lower) / (self.period - 1)

    @property
    def number_higher(self) -> float:
        """The current market meanness."""
        if not self.initialized:
            return np.nan

        prev = self._prices[1:]
        curr = self._prices[:-1]

        # The number of lower and higher reversions that were avoided.
        number_higher = np.sum((curr > self.median) & (curr > prev))

        return number_higher / (self.period - 1)

    @property
    def number_lower(self) -> float:
        """The current market meanness."""
        if not self.initialized:
            return np.nan

        prev = self._prices[1:]
        curr = self._prices[:-1]

        # The number of lower and higher reversions that were avoided.
        number_lower = np.sum((curr < self.median) & (curr < prev))

        return number_lower / (self.period - 1)

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

        self.median = np.median(self._prices)

        if not self.initialized:
            self._set_has_inputs(True)

            if not np.isnan(self._prices).any():
                self._set_initialized(True)

    def _reset(self):
        self._prices[:] = np.nan
        self.median = np.nan
