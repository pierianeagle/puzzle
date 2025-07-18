import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


def trace_candlesticks(df_bars: pd.DataFrame, colour_map: dict) -> go.Candlestick:
    """Create a standard candlestick trace."""
    candlestick_trace = go.Candlestick(
        x=df_bars.index,
        open=df_bars["open"],
        high=df_bars["high"],
        low=df_bars["low"],
        close=df_bars["close"],
        increasing=dict(
            line=dict(color=colour_map["increasing"]),
            fillcolor=colour_map["increasing"],
        ),
        decreasing=dict(
            line=dict(color=colour_map["decreasing"]),
            fillcolor=colour_map["decreasing"],
        ),
        opacity=0.75,
    )

    return candlestick_trace


def trace_volumes(df_bars: pd.DataFrame, colour_map: dict) -> go.Bar:
    """Create a standard bar trace."""
    bar_trace = go.Bar(
        x=df_bars.index,
        y=df_bars["volume"],
        marker=dict(
            color=np.where(
                df_bars["close"] > df_bars["open"],
                colour_map["increasing"],
                colour_map["decreasing"],
            ),
            line=dict(width=0),
        ),
        opacity=0.75,
    )

    return bar_trace


def plot_candlesticks_with_volumes(
    df_bars: pd.DataFrame,
    colour_map: dict | None = None,
) -> go.Figure:
    """Plot a standard candlestick and volume chart on a newly created figure."""
    if colour_map is None:
        template = pio.templates[pio.templates.default]

        colour_map = {
            "increasing": template.data.candlestick[0].increasing.line.color,
            "decreasing": template.data.candlestick[0].decreasing.line.color,
        }

    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.75, 0.25],
        vertical_spacing=0,
        shared_xaxes=True,
    )

    fig.append_trace(trace_candlesticks(df_bars, colour_map), row=1, col=1)
    fig.append_trace(trace_volumes(df_bars, colour_map), row=2, col=1)

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        xaxis2=dict(showgrid=True),
        showlegend=False,
    )

    return fig
