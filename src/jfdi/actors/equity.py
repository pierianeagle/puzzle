import pandas as pd
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.common.enums import LogColor
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


@customdataclass
class EquityData(Data):
    # Class variables can only be basic data types or instrument ids.
    # equity: Money = Money(0, Currency.from_str("USD"))
    equity: float = 0


class EquityActorConfig(ActorConfig):
    account_venue: Venue
    exchange_rate_venue: Venue
    # Multi-currency accounts have no base currency.
    reporting_currency: Currency
    start_time: pd.Timestamp
    component_id: ComponentId


class EquityActor(Actor):
    def __init__(self, config: EquityActorConfig) -> None:
        """Publish the account's equity.

        This actor publishes data on time events to avoid calculating every bar, and
        keeps the account and exchange rate venues separate to support Interactive
        Brokers.
        """
        super().__init__(config)

        self.equity_key = f"{self.config.account_venue}-EQUITY"
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
                    self.config.account_venue
                ).balances_total()

                # Accounts at IB trade at multiple venues in NT, which all have separate
                # profits and losses.
                venues = {
                    instrument.id.venue for instrument in self.cache.instruments()
                }

                unrealised_pnls = get_all_unrealised_pnls(self, venues)

                equities = get_equities(balances_total, unrealised_pnls)

                equity = get_equity(
                    self,
                    equities,
                    self.config.exchange_rate_venue,
                    self.config.reporting_currency,
                )

                if equity is None:
                    self.log.warning("NO EXCHANGE RATES AVAILABLE.", LogColor.CYAN)
                    return

                equity_data = EquityData(
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                    equity=equity.as_double(),
                )

                self.publish_data(
                    DataType(
                        EquityData,
                        metadata={
                            "venue": self.config.account_venue,
                            "currency_code": self.config.reporting_currency.code,
                        },
                    ),
                    equity_data,
                )


def get_all_unrealised_pnls(
    actor: Actor,
    venues: list[Venue],
) -> dict[Currency, Money]:
    unrealised_pnls = {}

    for venue in venues:
        for currency, money in actor.portfolio.unrealized_pnls(venue).items():
            unrealised_pnls[currency] = Money(
                unrealised_pnls.get(currency, 0) + money, currency
            )

    return unrealised_pnls


def get_equities(
    balances_total: dict[Currency, Money],
    unrealised_pnls: dict[Currency, Money],
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
    actor: Actor,
    equities: dict[Currency, Money],
    exchange_rate_venue: Venue,
    reporting_currency: Currency,
) -> Money:
    """Calculate the account value in the reporting currency."""
    equity = 0

    for currency, money in equities.items():
        exchange_rate = actor.cache.get_xrate(
            venue=exchange_rate_venue,
            from_currency=currency,
            to_currency=reporting_currency,
        )

        if exchange_rate is None:
            return None

        equity += money * exchange_rate

    equity = Money(equity, reporting_currency)

    return equity
