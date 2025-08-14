import pandas as pd
from nautilus_trader.cache import Cache
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.common.events import TimeEvent
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
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


@customdataclass
class EquityData(Data):
    # Class variables can only be basic data types or instrument ids.
    # equity: Money = Money(0, Currency.from_str("USD"))
    equity: float = 0


class EquityActorConfig(ActorConfig):
    venue: Venue
    # Multi-currency accounts have no base currency.
    reporting_currency: Currency
    start_time: pd.Timestamp
    component_id: ComponentId


class EquityActor(Actor):
    def __init__(self, config: EquityActorConfig) -> None:
        """Publish the account's equity.

        This actor does not support multi-currency accounts.
        """
        super().__init__(config)

        self.equity_key = f"{self.config.venue}-EQUITY"
        self.timer_key = f"{self.id}-TIMER"

    def on_start(self) -> None:
        self.clock.set_timer(
            name=self.timer_key,
            interval=pd.Timedelta(days=1),
            start_time=self.config.start_time,
        )

    def on_stop(self) -> None:
        pass

    def on_event(self, event: Event) -> None:
        if isinstance(event, TimeEvent):
            if event.name == self.timer_key:
                balances_total = self.portfolio.account(
                    self.config.venue
                ).balances_total()

                unrealised_pnls = self.portfolio.unrealized_pnls(self.config.venue)

                equities = get_equities(balances_total, unrealised_pnls)

                equity = get_equity(
                    equities, self.config.reporting_currency, self.cache
                )

                equity_data = EquityData(
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                    equity=equity.as_double(),
                )

                self.publish_data(
                    DataType(
                        EquityData,
                        metadata={
                            "venue": self.config.venue,
                            "currency_code": self.config.reporting_currency.code,
                        },
                    ),
                    equity_data,
                )


def get_equities(
    balances_total: dict[Currency, Money],
    unrealised_pnls: dict[InstrumentId, Money],
) -> dict[Currency, Money]:
    """Calculate the account value in each currency it's exposed to."""
    currencies = balances_total.keys() | unrealised_pnls.keys()

    # Unrealised pnls are reported in the settlement currency.
    equities = {
        currency: Money(
            balances_total.get(currency, Money(0, currency=currency)).as_double()
            + unrealised_pnls.get(currency, Money(0, currency=currency)).as_double(),
            currency,
        )
        for currency in currencies
    }

    return equities


def get_equity(
    equities: dict[Currency, Money],
    reporting_currency: Currency,
    cache: Cache,
) -> Money:
    """Calculate the account value in the reporting currency."""
    equity = 0

    for currency, money in equities.items():
        if currency == reporting_currency:
            equity += money
        else:
            exchange_rate = cache.get_mark_xrate(
                from_currency=currency, to_currency=reporting_currency
            )

            equity += money * exchange_rate

    equity = Money(equity, reporting_currency)

    return equity
