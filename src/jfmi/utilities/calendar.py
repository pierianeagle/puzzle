import pandas as pd
from nautilus_trader.model.instruments import Instrument


def process_interactive_brokers_trading_hours(instrument: Instrument) -> pd.DataFrame:
    """Clean the trading hours of an Interactive Brokers instrument."""
    sr_trading_hours = pd.Series(
        instrument.info["tradingHours"].split(";"), name="trading_hours"
    )

    df_trading_hours = sr_trading_hours.str.split("-", expand=True)

    df_trading_hours = df_trading_hours.apply(
        pd.to_datetime, format="%Y%m%d:%H%M", errors="coerce"
    ).dropna()
    df_trading_hours.columns = ["Opening Time", "Closing Time"]

    df_trading_hours.index = df_trading_hours["Opening Time"].dt.normalize()
    df_trading_hours.index.name = "Date"

    return df_trading_hours
