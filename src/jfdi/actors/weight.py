from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import ComponentId, DataType, InstrumentId
from nautilus_trader.model.custom import customdataclass

from jfdi.actors.equity import EquityData


@customdataclass
class WeightData(Data):
    instrument_id: str = ""
    weight: float = 0


class WeightActorConfig(ActorConfig):
    instrument_id: InstrumentId
    # Unique component ids are required if you want to run multiple components
    # of the same class.
    component_id: ComponentId


class WeightActor(Actor):
    def __init__(self, config: WeightActorConfig) -> None:
        """Publish the instrument's portfolio weight on account equity releases.

        This actor does not support multi-currency accounts.
        """
        super().__init__(config)

        self.weight_key = f"{self.config.instrument_id}-WEIGHT"

    def on_start(self) -> None:
        self.subscribe_data(
            DataType(
                EquityData,
                metadata={
                    "venue": self.config.instrument_id.venue,
                    "currency_code": self.portfolio.account(
                        self.config.instrument_id.venue
                    ).base_currency,
                },
            )
        )

    def on_stop(self) -> None:
        self.unsubscribe_data(
            DataType(
                EquityData,
                metadata={
                    "venue": self.config.instrument_id.venue,
                    "currency_code": self.portfolio.account(
                        self.config.instrument_id.venue
                    ).base_currency,
                },
            )
        )

    def on_data(self, data: Data) -> None:
        if isinstance(data, EquityData):
            account = self.portfolio.account(self.config.instrument_id.venue)
            currency = account.base_currency

            weight = (
                (self.portfolio.is_net_long(self.config.instrument_id) * 2 - 1)
                * self.portfolio.net_exposure(self.config.instrument_id).as_double()
                / data.equity
            )

            weight_data = WeightData(
                ts_event=data.ts_event,
                ts_init=data.ts_init,
                instrument_id=self.config.instrument_id,
                weight=weight,
            )

            self.publish_data(
                DataType(
                    WeightData,
                    metadata={
                        "currency_code": currency.code,
                    },
                ),
                weight_data,
            )
