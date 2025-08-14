import numpy as np
import pandas as pd
from nautilus_trader.common.actor import Actor, ActorConfig
from nautilus_trader.common.events import TimeEvent
from nautilus_trader.core import UUID4
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model import (
    AccountBalance,
    ComponentId,
    Currency,
    DataType,
    Money,
    Venue,
)
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.events import AccountState


@customdataclass
class BorrowingFeeData(Data):
    fee: float = 0


class BorrowingFeeActorConfig(ActorConfig):
    venue: Venue
    start_time: pd.Timestamp
    component_id: ComponentId


class BorrowingFeeActor(Actor):
    def __init__(self, config: BorrowingFeeActorConfig) -> None:
        """Interactive Brokers Pro Tiered margin loan fee actor (USD).

        This actor assumes that there will be a single account per venue, and does not
        support multi-currency accounts.
        """
        super().__init__(config)

        self.currency = Currency.from_str("USD")
        self.borrowing_fee_key = f"{self.config.venue}_BORROWING_FEE"
        self.timer_key = f"{self.id}_TIMER"

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

                account_balance = account.balance(self.currency)

                total_initial_notional_value = 0

                for position in self.cache.positions_open(self.config.venue):
                    total_initial_notional_value += (
                        position.avg_px_open * position.quantity
                    )

                borrowed_funds = total_initial_notional_value - account_balance.total

                borrowed_funds = float(borrowed_funds) if borrowed_funds > 0 else 0

                borrowing_fee = self.calculate_borrowing_fee(float(borrowed_funds))

                borrowing_fee_data = BorrowingFeeData(
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                    fee=borrowing_fee,
                )

                self.publish_data(
                    DataType(
                        BorrowingFeeData,
                        metadata={
                            "venue": self.config.venue,
                            "currency_code": self.currency.code,
                        },
                    ),
                    borrowing_fee_data,
                )

                # The exchange isn't accessible from inside actors, so I'm updating the
                # message bus manually.
                # exchange.adjust_account(Money(-borrowing_fee, currency))
                account_balance_dict = account_balance.to_dict()

                account_balance_dict["total"] = str(
                    Money(
                        account_balance.total - borrowing_fee, self.currency
                    ).as_decimal()
                )
                account_balance_dict["free"] = str(
                    Money(
                        account_balance.free - borrowing_fee, self.currency
                    ).as_decimal()
                )

                modified_account_balance = AccountBalance.from_dict(
                    account_balance_dict
                )

                account_state = AccountState(
                    account_id=account.id,
                    account_type=account.type,
                    base_currency=account.base_currency,
                    reported=False,
                    balances=[modified_account_balance],
                    margins=list(account.margins().values()),
                    info={},
                    event_id=UUID4(),
                    ts_event=self.clock.timestamp_ns(),
                    ts_init=event.ts_init,
                )

                self.msgbus.send(
                    endpoint="Portfolio.update_account",
                    msg=account_state,
                )

    def calculate_borrowing_fee(self, borrowed_funds: float) -> float:
        """Calculate the daily borrowing fee for a given amount of borrowed funds."""
        if borrowed_funds <= 0:
            return 0

        # Tiered interest rates in percentage terms (that should change with the
        # benchmark rate).
        rates = [
            (100_000, 0.0583),  # <100_000 USD, %
            (1_000_000, 0.0533),  # 100_000<1_000_000 USD, %
            (50_000_000, 0.0508),  # 1_000_000<50_000_000 USD, %
            (250_000_000, 0.0483),  # 50_000_000<250_000_000 USD, %
            (np.inf, 0.0483),  # 250_000_000< USD, %
        ]

        borrowing_fee = 0.0
        remaining_funds = borrowed_funds
        previous_tier_limit = 0

        for tier_limit, rate in rates:
            if remaining_funds <= 0:
                break

            tier_amount = min(tier_limit - previous_tier_limit, remaining_funds)

            # They use a rate basis of 360 days, not 365.
            borrowing_fee += tier_amount * rate / 360
            remaining_funds -= tier_amount
            previous_tier_limit = tier_limit

        return borrowing_fee
