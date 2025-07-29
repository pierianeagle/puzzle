import pandas as pd
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.common.events import TimeEvent
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model import ComponentId, DataType, Money, Venue
from nautilus_trader.model.custom import customdataclass


@customdataclass
class EquityData(Data):
    # Class variables can only be basic data types or instrument ids.
    # equity: Money = Money(0, Currency.from_str("USD"))
    equity: float = 0


class EquityActorConfig(ActorConfig):
    venue: Venue
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
                account = self.portfolio.account(self.config.venue)
                currency = account.base_currency

                balances_total = account.balances_total()
                unrealised_pnls = self.portfolio.unrealized_pnls(self.config.venue)

                currencies = balances_total.keys() | unrealised_pnls.keys()

                # Unrealised pnls are reported in the settlement currency.
                equities = {
                    currency: balances_total.get(
                        currency, Money(0, currency=currency)
                    ).as_double()
                    + unrealised_pnls.get(
                        currency, Money(0, currency=currency)
                    ).as_double()
                    for currency in currencies
                }

                equity_data = EquityData(
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                    equity=equities[currency],
                )

                self.publish_data(
                    DataType(
                        EquityData,
                        metadata={
                            "venue": self.config.venue,
                            "currency_code": currency.code,
                        },
                    ),
                    equity_data,
                )
