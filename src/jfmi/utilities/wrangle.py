import pandas as pd
from nautilus_trader.model import Bar, InstrumentId, TradeTick
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler


def unwrangle_bars(bars: list[Bar]) -> pd.DataFrame:
    """Transform wrangled bars back into a dataframe."""
    df_bars = pd.DataFrame(map(lambda bar: Bar.to_dict(bar), bars))

    df_bars.index = pd.to_datetime(df_bars["ts_event"], unit="ns", origin="unix")

    # Where "type" is the Data subclass (so is always Bar) but "bar_type" is
    # the BarType (so varies if there are multiple InstrumentIds).
    df_bars = df_bars.drop(columns=["type", "ts_init", "ts_event"], errors="ignore")

    numeric_columns = df_bars.columns.drop("bar_type")

    df_bars[numeric_columns] = df_bars[numeric_columns].apply(pd.to_numeric, axis=1)

    df_bars["volume"] = df_bars["volume"].astype(int)

    return df_bars


def wrangle_trade_ticks(
    df_bars: pd.DataFrame, instruments: list[Instrument]
) -> list[TradeTick]:
    """Transform a dataframe of bars into trade ticks."""
    wrangled_trade_ticks = []

    for name, group in df_bars.groupby("instrument_id"):
        instrument = next(
            filter(
                lambda equity: equity.id == InstrumentId.from_str(name), instruments
            ),
            None,
        )

        wrangler = TradeTickDataWrangler(instrument)

        wrangled_trade_ticks.extend(wrangler.process_bar_data(group))

    # Sort the trade ticks inplace.
    wrangled_trade_ticks.sort(key=lambda trade_tick: trade_tick.ts_event)

    return wrangled_trade_ticks
