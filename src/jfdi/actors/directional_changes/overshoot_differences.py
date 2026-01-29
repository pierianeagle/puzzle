from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import BarType, ComponentId, DataType
from nautilus_trader.model.custom import customdataclass

from jfdi.actors.directional_changes.extrema import ExtremaData


@customdataclass
class OvershootDifferenceData(Data):
    difference: float
    length: int  # pd.Timedelta
    previous_type: int  # ExtremaType
    current_type: int  # ExtremaType


class OvershootDifferenceActorConfig(ActorConfig):
    bar_type: BarType
    threshold: float
    current_overshoot: bool
    component_id: ComponentId


class OvershootDifferenceActor(Actor):
    def __init__(self, config: OvershootDifferenceActorConfig) -> None:
        """Publish the differences between extrema and overshoots.

        Always uses the previous extrema, not the previous high or low.

        Args:
            bar_type:
                The bars that the extrema are created from.
            threshold:
                The theshold that the extrema are created from.
            current_overshoot:
                Whether to compare the current overshoot or extrema to the previous
                overshoot.
            component_id:
                The ID to assign to this component.
        """
        super().__init__(config)

        self.swing_point_key = f"{self.config.bar_type}-SWING-POINT-DIFFERENCE"

        self.previous = None

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
            if self.previous:
                self.publish_data(
                    DataType(
                        OvershootDifferenceData,
                        metadata={
                            "bar_type": self.config.bar_type,
                            "threshold": self.config.threshold,
                        },
                    ),
                    OvershootDifferenceData(
                        ts_event=data.ts_event,
                        ts_init=data.ts_init,
                        difference=(
                            data.overshoot
                            if self.config.current_overshoot
                            else data.extrema
                        )
                        - self.previous.overshoot,
                        length=(
                            data.ts_init
                            if self.config.current_overshoot
                            else data.ts_event
                        )
                        - self.previous.ts_init,
                        previous_type=self.previous.extrema_type,
                        current_type=data.extrema_type,
                    ),
                )

            self.previous = data
