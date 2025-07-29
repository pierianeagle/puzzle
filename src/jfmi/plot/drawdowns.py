import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


def plot_drawdowns(
    df_equity: pd.DataFrame,
    df_drawdowns: pd.DataFrame,
    colour_map: dict | None = None,
) -> go.Figure:
    if colour_map is None:
        template = pio.templates[pio.templates.default]

        colour_map = {
            "line": template.data.scatter[0].line.color,
            "marker": template.data.scatter[0].marker.color,
            "increasing": template.data.candlestick[0].increasing.line.color,
            "decreasing": template.data.candlestick[0].decreasing.line.color,
            "right_censored": template.layout.meta["extras"]["right_censored"],
        }

    fig = go.Figure()

    # Plot the account's equity.
    fig.add_trace(
        go.Scatter(
            x=df_equity["equity"].index,
            y=df_equity["equity"],
            mode="lines",
            line=dict(color=colour_map["line"]),
            name="Account Equity",
        )
    )

    # Add markers for each draw down.
    fig.add_trace(
        go.Scatter(
            x=df_drawdowns["Start Index"],
            y=df_equity.loc[df_drawdowns["Start Index"], "equity"],
            mode="markers",
            marker=dict(color=colour_map["marker"]),
            name="Start",
            text=[
                f"<b>Start Index:</b> {start_index}<br>"
                f"<b>Value:</b> {valley:.2f}<br>"
                f"<b>Length:</b> {length}"
                for start_index, valley, length in zip(
                    df_drawdowns["Start Index"],
                    df_equity.loc[df_drawdowns["Start Index"], "equity"],
                    df_drawdowns["Length"],
                    strict=True,
                )
            ],
            hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_drawdowns["Bottom Index"],
            y=df_equity.loc[df_drawdowns["Bottom Index"], "equity"],
            mode="markers",
            marker=dict(color=colour_map["decreasing"]),
            name="Bottom",
            text=[
                f"<b>Bottom Index:</b> {bottom_index}<br>"
                f"<b>Value:</b> {valley:.4f}<br>"
                f"<b>Decline:</b> {decline:.4f}<br>"
                f"<b>Decline Length:</b> {decline_length}"
                for bottom_index, valley, decline, decline_length in zip(
                    df_drawdowns["Bottom Index"],
                    df_equity.loc[df_drawdowns["Bottom Index"], "equity"],
                    df_drawdowns["Decline"],
                    df_drawdowns["Decline Length"],
                    strict=True,
                )
            ],
            hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_drawdowns["End Index"],
            y=df_equity.loc[df_drawdowns["End Index"], "equity"],
            mode="markers",
            marker=dict(
                color=[
                    (
                        colour_map["right_censored"]
                        if idx == df_equity.index[-1]
                        else colour_map["increasing"]
                    )
                    for idx in df_drawdowns["End Index"]
                ]
            ),
            name="End",
            text=[
                f"<b>End Index:</b> {end_index}<br>"
                f"<b>Value:</b> {valley:.4f}<br>"
                f"<b>Recovery:</b> {recovery:.4f}<br>"
                f"<b>Recovery Length:</b> {recovery_length}"
                for end_index, valley, recovery, recovery_length in zip(
                    df_drawdowns["End Index"],
                    df_equity.loc[df_drawdowns["End Index"], "equity"],
                    df_drawdowns["Recovery"],
                    df_drawdowns["Recovery Length"],
                    strict=True,
                )
            ],
            hoverinfo="text",
        )
    )

    # Add vertical rectangles for each draw down.
    for _, row in df_drawdowns.iterrows():
        fig.add_vrect(
            x0=row["Start Index"],
            x1=row["Bottom Index"],
            fillcolor=colour_map["decreasing"],
            opacity=0.1,
            line_width=0,
            layer="below",
        )
        fig.add_vrect(
            x0=row["Bottom Index"],
            x1=row["End Index"],
            fillcolor=colour_map["increasing"],
            opacity=0.1,
            line_width=0,
            layer="below",
        )

    fig.update_traces(marker=dict(symbol="diamond", size=8))

    fig.update_layout(
        legend=dict(
            orientation="h",
            y=1.15,
            xanchor="left",
        ),
        autosize=False,
        width=800,
        height=400,
        margin=dict(l=50, r=50, b=50, t=40),
    )

    return fig
