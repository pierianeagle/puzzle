import numpy as np
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar

from jfdi.indicators.ehler.high_pass import compute_filter_coefficients
from jfdi.indicators.ehler.low_pass import update_band_pass


class UltimateRange(Indicator):
    def __init__(
        self,
        period_centre: int,
        period_str: int,
        n_ranges: float = 1.0,
    ):
        """Ehler's 'Ultimate Channel'.

        This indicator is akin to Bollinger bands, but uses a simplified version of the
        average true range to take ranges from the centre, reacting to large moves
        quickly.

        Args:
            period_centre: Lookback for the centre.
            period_str: Lookback for the simplified true range.
            n_ranges: The number of standard deviations to take from the centre.
            price_type: The price type to extract from ticks.
        """
        PyCondition.positive_int(period_centre, "period_centre")
        PyCondition.positive_int(period_str, "period_str")
        PyCondition.positive(n_ranges, "n_ranges")

        super().__init__(params=[period_centre, period_str, n_ranges])

        self.short_name = "u_rng"

        self.period_centre = period_centre
        self.period_str = period_str
        self.n_ranges = n_ranges

        self._closes = np.full(self.period_centre, np.nan)
        self._ranges = np.full(self.period_str, np.nan)

        self._band_pass_centre = np.zeros(2)
        self._band_pass_str = np.zeros(2)

        self._coefficients_centre = compute_filter_coefficients(period_centre)
        self._coefficients_str = compute_filter_coefficients(period_str)

    @property
    def simplified_true_range(self) -> float:
        if not self.initialized:
            return np.nan

        return self._band_pass_str[0]

    @property
    def centre(self) -> float:
        if not self.initialized:
            return np.nan

        return self._band_pass_centre[0]

    @property
    def upper_band(self) -> float:
        if not self.initialized:
            return np.nan

        return self.centre + self.n_ranges * self.simplified_true_range

    @property
    def lower_band(self) -> float:
        if not self.initialized:
            return np.nan

        return self.centre - self.n_ranges * self.simplified_true_range

    def handle_bar(self, bar: Bar):
        PyCondition.not_none(bar, "bar")

        self.update_raw(bar.close.as_double())

    def update_raw(self, bar: Bar):
        self._closes[1:] = self._closes[:-1]
        self._closes[0] = self.bar.close

        if not self.initialized:
            self._set_has_inputs(True)

            if np.count_nonzero(~np.isnan(self._closes)) < 1:
                return

        true_high = np.max(self.bar.high, self._closes[1])
        true_low = np.max(self.bar.low, self._closes[1])

        self._ranges[1:] = self._ranges[:-1]
        self._ranges[0] = true_high - true_low

        if not self.initialized:
            self._set_has_inputs(True)

            if np.count_nonzero(~np.isnan(self._ranges)) < 3:
                return

        self._band_pass_centre = update_band_pass(
            self._closes,
            self._band_pass_centre,
            self._coefficients_centre,
        )
        self._band_pass_str = update_band_pass(
            self._ranges,
            self._band_pass_str,
            self._coefficients_str,
        )

        if not self.initialized:
            self._set_initialized(True)

    def _reset(self):
        self._closes[:] = np.nan
        self._ranges[:] = np.nan
        self._band_pass_centre[:] = 0.0
        self._band_pass_str[:] = 0.0
