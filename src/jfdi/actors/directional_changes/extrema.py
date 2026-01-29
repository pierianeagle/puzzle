from enum import Enum, unique

import numpy as np
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import Bar, BarType, ComponentId, DataType, Price
from nautilus_trader.model.custom import customdataclass


@unique
class TrendType(Enum):
    UP = 1
    DOWN = 2


@unique
class ExtremaType(Enum):
    HIGH = 1
    LOW = 2


@customdataclass
class ExtremaData(Data):
    extrema: float  # Price
    overshoot: float  # Price
    extrema_type: int  # ExtremaType


class ExtremaActorConfig(ActorConfig):
    bar_type: BarType
    threshold: float
    component_id: ComponentId


class ExtremaActor(Actor):
    def __init__(self, config: ExtremaActorConfig) -> None:
        """Publish extrema by measuring from the high and low watermarks.

        Based upon Directional Changes, as described in Glattfelder, Dupuis, & Olsen
        (2010). Patterns in High-Frequency FX Data: Discovery of 12 Empirical Scaling
        Laws. Quantitative Finance,  11(4), pp.599-614. Available at:
        https://doi.org/10.1080/14697688.2010.481632

        Each data object consists of two values: the `extrema` price at `ts_event`, and
        the `overshoot` price, the price when the reversal was confirmed, at `ts_init`.

        Args:
            bar_type: The bars to monitor.
            threshold: An arbitrary theshold that determines the scale of events.
            component_id: The ID to assign to this component.
        """
        super().__init__(config)

        self.swing_point_key = f"{self.config.bar_type}-SWING-POINT"

        self.trend = TrendType.UP

        self.high_water_mark = 0
        self.low_water_mark = 0

        self.ts_start = 0
        self.ts_end = 0

    def on_start(self) -> None:
        self.subscribe_bars(self.config.bar_type)

    def on_stop(self) -> None:
        self.unsubscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        bar = transform_bar(bar)

        if self.high_water_mark == 0:
            self.high_water_mark = bar.high
        if self.low_water_mark == 0:
            self.low_water_mark = bar.low
        if self.ts_start == 0:
            self.ts_start = bar.ts_event
        if self.ts_end == 0:
            self.ts_end = bar.ts_event

        if self.trend == TrendType.UP:
            if bar.low < (1 - self.config.threshold) * self.high_water_mark:
                self.trend = TrendType.DOWN
                self.low_water_mark = bar.low
                self.ts_end = bar.ts_event

                self.publish_data(
                    DataType(
                        ExtremaData,
                        metadata={
                            "bar_type": self.config.bar_type,
                            "threshold": self.config.threshold,
                        },
                    ),
                    ExtremaData(
                        ts_event=self.ts_start,
                        ts_init=bar.ts_event,
                        extrema=self.high_water_mark.as_double(),
                        overshoot=bar.close.as_double(),
                        extrema_type=ExtremaType.HIGH.value,
                    ),
                )
            else:
                if bar.high > self.high_water_mark:
                    self.high_water_mark = bar.high
                    self.ts_start = bar.ts_event
        else:
            if bar.high > (1 + self.config.threshold) * self.low_water_mark:
                self.trend = TrendType.UP
                self.high_water_mark = bar.high
                self.ts_start = bar.ts_event

                self.publish_data(
                    DataType(
                        ExtremaData,
                        metadata={
                            "bar_type": self.config.bar_type,
                            "threshold": self.config.threshold,
                        },
                    ),
                    ExtremaData(
                        ts_event=self.ts_end,
                        ts_init=bar.ts_event,
                        extrema=self.low_water_mark.as_double(),
                        overshoot=bar.close.as_double(),
                        extrema_type=ExtremaType.LOW.value,
                    ),
                )
            else:
                if bar.low < self.low_water_mark:
                    self.low_water_mark = bar.low
                    self.ts_end = bar.ts_event


def transform_bar(bar: Bar) -> Bar:
    """Get the logarithm of the bar."""
    bar_dict = Bar.to_dict(bar)

    bar_dict["open"] = str(np.log(bar.close.as_double()))
    bar_dict["high"] = str(np.log(bar.high.as_double()))
    bar_dict["low"] = str(np.log(bar.low.as_double()))
    bar_dict["close"] = str(np.log(bar.close.as_double()))

    bar = Bar.from_dict(bar_dict)

    return bar
