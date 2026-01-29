import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType

from jfdi.indicators.ehler.high_pass import compute_filter_coefficients
from jfdi.indicators.ehler.low_pass import update_low_pass


class UltimateBands(Indicator):
    def __init__(
        self,
        period: int,
        n_deviations: float = 1.0,
        price_type: PriceType = PriceType.LAST,
    ):
        """Ehler's 'Ultimate Bands'.

        This indicator is akin to Bollinger bands in that it takes standard deviations
        of prices from the centre, reacting to the moves over the period.

        Args:
            period: Lookback.
            n_deviations: The number of standard deviations to take from the centre.
            price_type: The price type to extract from ticks.
        """
        PyCondition.positive_int(period, "period")
        PyCondition.positive(n_deviations, "n_deviations")

        super().__init__(params=[period, n_deviations, price_type])

        self.short_name = "u_bnd"

        self.period = period
        self.n_deviations = n_deviations
        self.price_type = price_type

        self._prices = np.full(period, np.nan)
        self._centre = np.zeros(2)

        self._coefficients = compute_filter_coefficients(period)

    @property
    def standard_deviation(self) -> float:
        if not self.initialized:
            return np.nan

        return np.sqrt(np.mean((self._prices - self._centre[0]) ** 2))

    @property
    def centre(self) -> float:
        if not self.initialized:
            return np.nan

        return self._centre[0]

    @property
    def upper_band(self) -> float:
        if not self.initialized:
            return np.nan

        return self.centre + self.n_deviations * self.standard_deviation

    @property
    def lower_band(self) -> float:
        if not self.initialized:
            return np.nan

        return self.centre - self.n_deviations * self.standard_deviation

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

        self._centre = update_low_pass(
            self._prices,
            self._centre,
            self._coefficients,
        )

        if not self.initialized:
            self._set_initialized(True)

    def _reset(self):
        self._prices[:] = np.nan
        self._centre[:] = 0.0
