import plotly.graph_objects as go

COLOURS = {
    "black": "#1b1f23",
    "white": "#ffffff",
    "grey": [
        "#fafbfc",
        "#f6f8fa",
        "#e1e4e8",
        "#d1d5da",
        "#959da5",
        "#6a737d",
        "#586069",
        "#444d56",
        "#2f363d",
        "#24292e",
    ],
    "blue": [
        "#f1f8ff",
        "#dbedff",
        "#c8e1ff",
        "#79b8ff",
        "#2188ff",
        "#0366d6",
        "#005cc5",
        "#044289",
        "#032f62",
        "#05264c",
    ],
    "green": [
        "#f0fff4",
        "#dcffe4",
        "#bef5cb",
        "#85e89d",
        "#34d058",
        "#28a745",
        "#22863a",
        "#176f2c",
        "#165c26",
        "#144620",
    ],
    "yellow": [
        "#fffdef",
        "#fffbdd",
        "#fff5b1",
        "#ffea7f",
        "#ffdf5d",
        "#ffd33d",
        "#f9c513",
        "#dbab09",
        "#b08800",
        "#735c0f",
    ],
    "orange": [
        "#fff8f2",
        "#ffebda",
        "#ffd1ac",
        "#ffab70",
        "#fb8532",
        "#f66a0a",
        "#e36209",
        "#d15704",
        "#c24e00",
        "#a04100",
    ],
    "red": [
        "#ffeef0",
        "#ffdce0",
        "#fdaeb7",
        "#f97583",
        "#ea4a5a",
        "#d73a49",
        "#cb2431",
        "#b31d28",
        "#9e1c23",
        "#86181d",
    ],
    "purple": [
        "#f5f0ff",
        "#e6dcfd",
        "#d1bcf9",
        "#b392f0",
        "#8a63d2",
        "#6f42c1",
        "#5a32a3",
        "#4c2889",
        "#3a1d6e",
        "#29134e",
    ],
    "pink": [
        "#ffeef8",
        "#fedbf0",
        "#f9b3dd",
        "#f692ce",
        "#ec6cb9",
        "#ea4aaa",
        "#d03592",
        "#b93a86",
        "#99306f",
        "#6d224f",
    ],
}

TEMPLATE_DARK = go.layout.Template(
    data=dict(
        candlestick=[
            dict(
                increasing=dict(
                    line=dict(color=COLOURS["green"][4]),
                    fillcolor=COLOURS["green"][4],
                ),
                decreasing=dict(
                    line=dict(color=COLOURS["red"][4]),
                    fillcolor=COLOURS["red"][4],
                ),
            )
        ],
        scatter=[
            dict(
                line=dict(color=COLOURS["purple"][4]),
                marker=dict(color=COLOURS["blue"][4]),
            )
        ],
    ),
    layout=dict(
        paper_bgcolor=COLOURS["grey"][9],
        plot_bgcolor=COLOURS["grey"][9],
        font=dict(color=COLOURS["grey"][2]),
        title=dict(font=dict(color=COLOURS["grey"][2])),
        xaxis=dict(
            color=COLOURS["grey"][4],
            linecolor=COLOURS["grey"][7],
            gridcolor=COLOURS["grey"][8],
            zerolinecolor=COLOURS["grey"][8],
            tickcolor=COLOURS["grey"][8],
            ticks="outside",
        ),
        yaxis=dict(
            color=COLOURS["grey"][4],
            linecolor=COLOURS["grey"][7],
            gridcolor=COLOURS["grey"][8],
            zerolinecolor=COLOURS["grey"][8],
            tickcolor=COLOURS["grey"][8],
            ticks="outside",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLOURS["grey"][4]),
        ),
        colorway=[
            COLOURS["blue"][4],
            COLOURS["green"][4],
            COLOURS["orange"][4],
            COLOURS["red"][4],
            COLOURS["purple"][4],
            COLOURS["pink"][4],
            COLOURS["yellow"][4],
        ],
        # A hack-y work-around to store additional colours.
        meta={
            "extras": {
                "right_censored": COLOURS["yellow"][4],
            }
        },
    ),
)

TEMPLATE_LAYOUT = go.layout.Template(
    layout=dict(
        title=dict(
            x=0.10,
            y=0.95,
            xanchor="left",
        ),
        xaxis=dict(
            showline=True,
            mirror=True,
        ),
        yaxis=dict(
            showline=True,
            mirror=True,
        ),
        legend=dict(
            orientation="h",
            y=1.15,
            xanchor="left",
        ),
        autosize=False,
        width=800,
        height=400,
        margin=dict(
            t=40,
            b=50,
            l=50,
            r=50,
        ),
    )
)
