from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import BarType, ComponentId, DataType
from nautilus_trader.model.custom import customdataclass

from jfdi.actors.directional_changes.extrema import ExtremaData, ExtremaType


@customdataclass
class ExtremaDifferenceData(Data):
    difference: float
    lag: int  # pd.Timedelta
    previous_type: int  # ExtremaType
    current_type: int  # ExtremaType


class ExtremaDifferenceActorConfig(ActorConfig):
    bar_type: BarType
    threshold: float
    previous_type: ExtremaType
    current_type: ExtremaType
    component_id: ComponentId


class ExtremaDifferenceActor(Actor):
    def __init__(self, config: ExtremaDifferenceActorConfig) -> None:
        """Publish the differences between extrema.

        Because highs and lows alternate, subscribing to both low-high and high-low
        differences provides the previous extrema, which can be useful as a measure of
        volatility. On the other hand, subcribing to the high-high or low-low
        differences can be useful as a measure of trend to measure higher or lower highs
        or lows.

        Args:
            bar_type: The bars that the extrema are created from.
            threshold: The theshold that the extrema are created from.
            previous_type: Whether to measure from previous highs or lows.
            current_type: Whether to measure from current highs or lows.
            component_id: The ID to assign to this component.
        """
        super().__init__(config)

        self.swing_point_key = f"{self.config.bar_type}-SWING-POINT-DIFFERENCE"

        self.previous = None
        self.current = None

    def on_start(self) -> None:
        self.subscribe_data(
            DataType(
                ExtremaData,
                metadata={
                    "bar_type": self.config.bar_type,
                    "threshold": self.config.threshold,
                },
            )
        )

    def on_stop(self) -> None:
        self.unsubscribe_data(
            DataType(
                ExtremaData,
                metadata={
                    "bar_type": self.config.bar_type,
                    "threshold": self.config.threshold,
                },
            )
        )

    def on_data(self, data: Data) -> None:
        if isinstance(data, ExtremaData):
            # If we're comparing highs to highs or lows to lows:
            if self.config.current_type == self.config.previous_type:
                if data.extrema_type == self.config.current_type.value:
                    self.previous = self.current
                    self.current = data

                    if self.previous and self.current:
                        self.publish_data(
                            DataType(
                                ExtremaDifferenceData,
                                metadata={
                                    "bar_type": self.config.bar_type,
                                    "threshold": self.config.threshold,
                                },
                            ),
                            ExtremaDifferenceData(
                                ts_event=self.current.ts_event,
                                ts_init=self.current.ts_init,
                                difference=self.current.extrema - self.previous.extrema,
                                lag=self.current.ts_init - self.previous.ts_init,
                                previous_type=self.config.previous_type.value,
                                current_type=self.config.current_type.value,
                            ),
                        )

                        return

            # If we're comparing higs to lows or lows to highs:
            elif data.extrema_type == self.config.current_type.value:
                self.current = data
            elif data.extrema_type == self.config.previous_type.value:
                self.previous = data

            if self.previous and self.current:
                if self.current.ts_init > self.previous.ts_init:
                    self.publish_data(
                        DataType(
                            ExtremaDifferenceData,
                            metadata={
                                "bar_type": self.config.bar_type,
                                "threshold": self.config.threshold,
                            },
                        ),
                        ExtremaDifferenceData(
                            ts_event=self.current.ts_event,
                            ts_init=self.current.ts_init,
                            difference=self.current.extrema - self.previous.extrema,
                            lag=self.current.ts_init - self.previous.ts_init,
                            previous_type=self.config.previous_type.value,
                            current_type=self.config.current_type.value,
                        ),
                    )

                    return
