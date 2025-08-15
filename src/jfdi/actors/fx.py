import pandas as pd
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.model import BarType, ComponentId


class FXActorConfig(ActorConfig):
    bar_types: list[BarType]
    component_id: ComponentId


class FXActor(Actor):
    def __init__(self, config: FXActorConfig) -> None:
        """Subcribe to exchange rate data to load it into the cache.

        You have to subscribe to either quote ticks or both bid and ask bars to populate
        the exchange rate quote tables.
        """
        super().__init__(config)

    def on_start(self) -> None:
        for bar_type in self.config.bar_types:
            self.request_bars(bar_type)
            self.subscribe_bars(bar_type)

    def on_stop(self) -> None:
        for bar_type in self.config.bar_types:
            self.unsubscribe_bars(bar_type)
