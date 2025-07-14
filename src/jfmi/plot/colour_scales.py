import numpy as np
import plotly.graph_objects as go


def plot_colour_scale(colour_scale: list[str]) -> go.Figure:
    """Plot a plotly colour-scale.

    Typical usage example:
    >>> colour_scale = px.colors.sequential.Viridis
    ... fig = plot_colour_scale(colour_scale)
    """
    n_colours = len(colour_scale)

    fig = go.Figure(
        go.Heatmap(
            z=np.arange(n_colours).reshape(1, -1),
            colorscale=[
                [i / (n_colours - 1), color] for i, color in enumerate(colour_scale)
            ],
            showscale=False,
            y=[0],
            x=np.linspace(0, 1, n_colours),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        height=100,
        width=600,
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
        ),
    )

    return fig


def plot_continuous_colour_scale(
    continuous_colour_scale: list[list[float, str]],
) -> go.Figure:
    """Plot a plotly continuous colour-scale.

    Typical usage example:
    >>> colour_scale = px.colors.sequential.Viridis
    ... continuous_colour_scale = px.colors.make_colorscale(colour_scale)
    ... fig = plot_continuous_colour_scale(continuous_colour_scale)
    """
    fig = go.Figure(
        go.Heatmap(
            z=np.linspace(0, 1, 100).reshape(1, -1),
            colorscale=continuous_colour_scale,
            showscale=False,
            y=[0],
            x=np.linspace(0, 1, 100),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        height=100,
        width=600,
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
        ),
    )

    return fig
