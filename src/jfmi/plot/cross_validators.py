import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
import plotly.io as pio


def plot_cross_validator_splits(
    df_bounds: pd.DataFrame,
    index: pd.DatetimeIndex,
    continuous_colour_scale: list[list[float, str]] | None = None,
) -> go.Figure:
    """Plot a scikit-learn cross-validator's test/train splits.

    Args:
        df_bounds:
            A multi-indexed DataFrame with `split` and `set` index levels, and `start`
            and `end` columns representing the first and last dates of each contiguous
            segment of the training and testing sets for each split.
        index:
            An index corresponding to the dataset being split.
        continuous_colour_scale:
            A plotly colour scale.

    Typical usage example:
    >>> df_bounds = get_cross_validator_bounds(df.index, cv.split(df[features]))
    ... colour_scale = px.colors.sequential.Viridis
    ... continuous_colour_scale = px.colors.make_colorscale(colour_scale)
    ... fig = plot_cross_validator_splits(df_bounds, df.index, continuous_colour_scale)
    """
    # If the colour scale wasn't supplied, grab it from the theme.
    if continuous_colour_scale is None:
        template = pio.templates[pio.templates.default]

        continuous_colour_scale = template.layout.colorscale.sequential

        # Plotly's default themes can have tuples, not lists, which for some reason
        # aren't compatible with their sample colourscale function.
        continuous_colour_scale = list(list(pair) for pair in continuous_colour_scale)

    # Initialise the pivot tables.
    n_splits = df_bounds.index.get_level_values("split").max() + 1

    df_matrix = pd.DataFrame(pd.NA, index=range(n_splits), columns=index)
    df_hover = pd.DataFrame(pd.NA, index=range(n_splits), columns=index)

    # Assign integer values to each unique set.
    unique_sets = df_bounds.index.get_level_values("set").unique()
    dict_set_values = {name: i + 1 for i, name in enumerate(unique_sets)}

    # Populate the pivot tables with each set's integer value and metadata.
    for (split, set_type), row in df_bounds.iterrows():
        mask = (row["start_time"] <= index) & (index <= row["end_time"])

        df_matrix.loc[split, mask] = dict_set_values[set_type]

        # "<br>".join([f"{col}: {row[col]}" for col in df_bounds.columns])
        df_hover.loc[split, mask] = (
            f"set: {set_type}<br>"
            f"start_time: {row['start_time']}<br>"
            f"end_time: {row['end_time']}<br>"
        )

    fig = go.Figure(
        data=go.Heatmap(
            z=df_matrix.values,
            x=df_matrix.columns,
            y=df_matrix.index,
            colorscale=continuous_colour_scale,
            showscale=False,
            hoverinfo="text",
            text=df_hover.values,
        )
    )

    # Add legend entries using invisible lines.
    n_sets = len(dict_set_values)

    colours = pc.sample_colorscale(
        continuous_colour_scale, list(np.linspace(0, 1, n_sets))
    )

    dict_set_colours = dict(zip(unique_sets, colours, strict=True))

    for set_name, set_colour in dict_set_colours.items():
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color=set_colour, width=7.5),
                name=set_name.capitalize(),
                showlegend=True,
            )
        )

    fig.update_layout(
        xaxis=dict(
            title="Date",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Split",
            showgrid=False,
            zeroline=False,
            autorange="reversed",
            dtick=1,
        ),
    )

    return fig
