import numpy as np
import numpy.typing as npt
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType


class ZLEMA(Indicator):
    def __init__(
        self,
        period: int,
        price_type: PriceType = PriceType.LAST,
    ):
        """The Zero-Lag Exponential Moving Average.

        An exponential moving average with adaptive gain correction to reduce lag.

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

        self._error = 1000000
        self._alpha = 2.0 / (self.period + 1.0)

        self._count = 0
        self._ema = np.nan
        self._zlema = np.full(2, np.nan)
        self._gain = 0.0

    @property
    def value(self) -> float:
        if not self.initialized:
            return np.nan

        return self._zlema[0]

    @staticmethod
    def calculate_zlema(
        alpha: float,
        ema: float,
        gain: float,
        value: float,
        zlema: npt.NDArray[np.floating],
    ):
        return alpha * (ema + gain * (value - zlema[1])) + (1 - alpha) * zlema[1]

    def _increment_count(self):
        self._count += 1

        if not self.initialized:
            self._set_has_inputs(True)

            if self._count >= self.period:
                self._set_initialized(True)

    def _calculate_gain(
        self,
        value: float,
        ema: float,
    ) -> float:
        gains = np.arange(-5.0, 5.0, 0.1)

        trials = self.calculate_zlema(self._alpha, self._ema, gains, value, self._zlema)
        errors = np.abs(value - trials)

        best_gain = gains[np.argmin(errors)]

        return best_gain

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
        # Check if this is the initial input.
        if not self.has_inputs:
            self._ema = value
            self._zlema[:] = value

        self._ema = self._alpha * value + (1.0 - self._alpha) * self._ema
        self._gain = self._calculate_gain(value, self._ema)

        zlema = self.calculate_zlema(
            self._alpha, self._ema, self._gain, value, self._zlema
        )

        self._zlema[1] = self._zlema[0]
        self._zlema[0] = zlema

        self._increment_count()

    def _reset(self):
        self.count = 0
        self._ema = np.nan
        self._zlema = np.full(2, np.nan)
        self._gain = 0.0
