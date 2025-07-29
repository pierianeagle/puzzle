import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go

from jfmi.plot.utilities import unparse_rgba_tuple


def plot_weights(
    df_weights: pd.DataFrame,
    colour_scale: list[str],
    absolute=False,
) -> go.Figure:
    fig = go.Figure()

    colour_iterator = iter(colour_scale)

    for name, group in df_weights.groupby("instrument_id"):
        opacity = 0.3

        colour = (*pc.hex_to_rgb(next(colour_iterator)), opacity)  # (r, g, b, a)
        colour_string = unparse_rgba_tuple(colour)

        fig.add_trace(
            go.Scatter(
                x=group.index,
                y=group["weight"] if not absolute else group["weight"].abs(),
                mode="lines",
                line=dict(
                    color=colour_string.replace(str(opacity), "1.0"),
                    width=2.0,
                ),
                fillcolor=colour_string,
                name=name,
                stackgroup="one",
            )
        )

    return fig
