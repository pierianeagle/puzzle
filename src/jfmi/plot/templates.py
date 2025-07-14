import plotly.graph_objects as go

# TODO - Use Visual Studio Code GitHub Theme colours to extend me.
TEMPLATE_DARK = go.layout.Template(
    layout=dict(
        paper_bgcolor="#2f363d",
        plot_bgcolor="#2f363d",
        font=dict(color="#f2f2f2"),
    )
)

TEMPLATE_LAYOUT = go.layout.Template(
    layout=dict(
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
)
