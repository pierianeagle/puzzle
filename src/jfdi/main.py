import os

from nautilus_trader.adapters.interactive_brokers.common import IB
from nautilus_trader.adapters.interactive_brokers.config import (
    IBMarketDataTypeEnum,
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersExecClientConfig,
    InteractiveBrokersInstrumentProviderConfig,
    SymbologyMethod,
)
from nautilus_trader.adapters.interactive_brokers.factories import (
    InteractiveBrokersLiveDataClientFactory,
    InteractiveBrokersLiveExecClientFactory,
)
from nautilus_trader.config import (
    LiveDataEngineConfig,
    LoggingConfig,
    RoutingConfig,
    TradingNodeConfig,
)
from nautilus_trader.examples.strategies.subscribe import (
    SubscribeStrategy,
    SubscribeStrategyConfig,
)
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId

test_instrument_str = "SPY.ARCA"
instrument_provider = InteractiveBrokersInstrumentProviderConfig(
    symbology_method=SymbologyMethod.IB_SIMPLIFIED,
    load_ids=frozenset([test_instrument_str]),
)

config_node = TradingNodeConfig(
    trader_id="TESTER-001",
    logging=LoggingConfig(log_level="INFO"),
    data_clients={
        IB: InteractiveBrokersDataClientConfig(
            ibg_host=os.environ["IBG_HOST"],
            ibg_port=int(os.environ["IBG_PAPER_PORT"]),
            ibg_client_id=1,
            handle_revised_bars=False,
            use_regular_trading_hours=True,
            market_data_type=IBMarketDataTypeEnum.DELAYED_FROZEN,
            instrument_provider=instrument_provider,
        ),
    },
    exec_clients={
        IB: InteractiveBrokersExecClientConfig(
            ibg_host=os.environ["IBG_HOST"],
            ibg_port=int(os.environ["IBG_PAPER_PORT"]),
            ibg_client_id=1,
            account_id=os.environ["IB_PAPER_ACCOUNT_ID"],
            instrument_provider=instrument_provider,
            routing=RoutingConfig(
                default=True,
            ),
        ),
    },
    data_engine=LiveDataEngineConfig(
        time_bars_timestamp_on_close=False,
        validate_data_sequence=True,
    ),
    timeout_connection=90.0,
    timeout_reconciliation=5.0,
    timeout_portfolio=5.0,
    timeout_disconnection=5.0,
    timeout_post_stop=2.0,
)

node = TradingNode(config=config_node)

strategy_config = SubscribeStrategyConfig(
    instrument_id=InstrumentId.from_str(test_instrument_str),
    trade_ticks=False,
    quote_ticks=False,
    bars=True,
)
strategy = SubscribeStrategy(config=strategy_config)

node.trader.add_strategy(strategy)

node.add_data_client_factory(IB, InteractiveBrokersLiveDataClientFactory)
node.add_exec_client_factory(IB, InteractiveBrokersLiveExecClientFactory)
node.build()

if __name__ == "__main__":
    try:
        node.run()
    finally:
        node.dispose()
