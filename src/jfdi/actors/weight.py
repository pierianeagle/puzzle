from nautilus_trader.cache import Cache
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model import (
    ComponentId,
    Currency,
    DataType,
    InstrumentId,
    Money,
    Venue,
)
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.portfolio import Portfolio

from jfdi.actors.equity import EquityData


@customdataclass
class WeightData(Data):
    instrument_id: str = ""
    weight: float = 0


class WeightActorConfig(ActorConfig):
    instrument_id: InstrumentId
    # This has to be its own argument because `IB_VENUE` is not `instrument_id.venue`.
    venue: Venue
    reporting_currency: Currency
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
        self.instrument = self.cache.instrument(self.config.instrument_id)

        if self.instrument is None:
            self.log.error(
                f"Could not find instrument. instrument_id: {self.config.instrument_id}"
            )
            self.stop()
            return

        self.subscribe_data(
            DataType(
                EquityData,
                metadata={
                    "venue": self.config.venue,
                    "currency_code": self.config.reporting_currency,
                },
            )
        )

    def on_stop(self) -> None:
        self.unsubscribe_data(
            DataType(
                EquityData,
                metadata={
                    "venue": self.config.venue,
                    "currency_code": self.config.reporting_currency,
                },
            )
        )

    def on_data(self, data: Data) -> None:
        if isinstance(data, EquityData):
            weight = get_weight(
                self.instrument,
                data.equity,
                self.config.venue,
                self.config.reporting_currency,
                self.portfolio,
                self.cache,
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
                        "venue": self.config.venue,
                        "currency_code": self.config.reporting_currency.code,
                    },
                ),
                weight_data,
            )


def get_weight(
    instrument: Instrument,
    account_equity: Money,
    exchange_rate_venue: Venue,
    reporting_currency: Currency,
    portfolio: Portfolio,
    cache: Cache,
) -> float:
    """Calculate the instrument weight in the reporting currency."""
    weight = (
        # If the portfolio is short multiply the allocation by -1.
        (portfolio.is_net_long(instrument.id) * 2 - 1)
        * portfolio.net_exposure(instrument.id).as_double()
        * cache.get_xrate(
            venue=exchange_rate_venue,
            from_currency=instrument.get_cost_currency(),
            to_currency=reporting_currency,
        )
        / account_equity
    )
    return weight
