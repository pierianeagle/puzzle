import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType

from jfdi.indicators.ehler.high_pass import (
    compute_filter_coefficients,
    update_high_pass,
)


class UltimateOscillator(Indicator):
    def __init__(
        self,
        edge: int,
        width: int,
        root_mean_square_period: int = 100,
        price_type: PriceType = PriceType.LAST,
    ):
        """Ehler's 'Ultimate Oscillator'.

        Args:
            edge: Edge period for high-pass filter.
            width: Width multiplier for high-pass filter.
            root_mean_square_period: Lookback for root-mean-square smoothing.
            price_type: Price type to extract from ticks.
        """
        PyCondition.positive_int(edge, "edge")
        PyCondition.positive_int(width, "width")
        PyCondition.positive_int(root_mean_square_period, "root_mean_square_period")

        super().__init__(params=[edge, width, root_mean_square_period, price_type])

        self.short_name = "u_osc"

        self.edge = edge
        self.width = width
        self.root_mean_square_period = root_mean_square_period
        self.price_type = price_type

        self._prices = np.full(3, np.nan)

        self._high_pass_edge = np.zeros(2)
        self._high_pass_width_edge = np.zeros(2)

        self._signals = np.full(root_mean_square_period, np.nan)

        self._coefficients_edge = compute_filter_coefficients(self.edge)
        self._coefficients_width_edge = compute_filter_coefficients(
            self.width * self.edge
        )

    @property
    def value(self) -> float:
        if not self.initialized:
            return np.nan

        signal = self._signals[0]
        root_mean_square = np.sqrt(np.mean(self._signals**2)) or 1e-10

        return signal / root_mean_square

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

            if np.count_nonzero(~np.isnan(self._prices)) < 3:
                return

        self._high_pass_edge = update_high_pass(
            self._prices,
            self._high_pass_edge,
            self._coefficients_edge,
        )
        self._high_pass_width_edge = update_high_pass(
            self._prices,
            self._high_pass_width_edge,
            self._coefficients_width_edge,
        )

        self._signals[1:] = self._signals[:-1]
        self._signals[0] = self._high_pass_width_edge[0] - self._high_pass_edge[0]

        if not self.initialized:
            if not np.isnan(self._signals).any():
                self._set_initialized(True)

    def _reset(self):
        self._prices[:] = np.nan
        self._high_pass_edge[:] = 0.0
        self._high_pass_width_edge[:] = 0.0
        self._signals[:] = np.nan
