from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import BarType, ComponentId, DataType
from nautilus_trader.model.custom import customdataclass

from jfdi.actors.directional_changes.extrema import ExtremaType
from jfdi.actors.directional_changes.extrema_difference import ExtremaDifferenceData


@customdataclass
class ExtremaSecondDifferenceData(Data):
    second_difference: float
    second_lag: int
    previous_type: int  # ExtremaType
    current_type: int  # ExtremaType


class ExtremaSecondDifferenceActorConfig(ActorConfig):
    bar_type: BarType
    threshold: float
    previous_type: ExtremaType
    current_type: ExtremaType
    component_id: ComponentId


class ExtremaSecondDifferenceActor(Actor):
    def __init__(self, config: ExtremaSecondDifferenceActorConfig) -> None:
        """Publish the differences of differences between extrema.

        Args:
            bar_type: The bars that the extrema are created from.
            threshold: The theshold that the extrema are created from.
            previous_type: Whether to measure from previous highs or lows.
            current_type: Whether to measure from current highs or lows.
            component_id: The ID to assign to this component.
        """
        super().__init__(config)

        self.swing_point_key = (
            f"{self.config.bar_type}-{self.config.threshold}-SWING-POINT-SECOND-"
            f"DIFFERENCE"
        )

        self.previous = None
        self.current = None

    def on_start(self) -> None:
        self.subscribe_data(
            DataType(
                ExtremaDifferenceData,
                metadata={
                    "bar_type": self.config.bar_type,
                    "threshold": self.config.threshold,
                },
            )
        )

    def on_stop(self) -> None:
        self.unsubscribe_data(
            DataType(
                ExtremaDifferenceData,
                metadata={
                    "bar_type": self.config.bar_type,
                    "threshold": self.config.threshold,
                },
            )
        )

    def on_data(self, data: Data) -> None:
        if isinstance(data, ExtremaDifferenceData):
            if (
                data.previous_type == self.config.previous_type.value
                and data.current_type == self.config.current_type.value
            ):
                self.previous = self.current
                self.current = data

                if self.previous and self.current:
                    self.publish_data(
                        DataType(
                            ExtremaSecondDifferenceData,
                            metadata={
                                "bar_type": self.config.bar_type,
                                "threshold": self.config.threshold,
                            },
                        ),
                        ExtremaSecondDifferenceData(
                            ts_event=self.current.ts_event,
                            ts_init=self.current.ts_init,
                            second_difference=self.current.difference
                            - self.previous.difference,
                            second_lag=self.current.ts_init - self.previous.ts_init,
                            previous_type=self.config.previous_type.value,
                            current_type=self.config.current_type.value,
                        ),
                    )
