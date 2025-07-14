import re

import plotly.colors as pc
import plotly.graph_objects as go
import plotly.io as pio


def load_plotly_templates(
    templates: dict[str, go.layout.Template] | None = None,
) -> None:
    """Load plot configuration from plotly templates.

    Whilst this function is a little ugly, I've found myself doing this again and again.
    """
    if templates is None:
        from jfmi.plot.templates import TEMPLATE_DARK, TEMPLATE_LAYOUT

        templates = {
            "dark": TEMPLATE_DARK,
            "layout": TEMPLATE_LAYOUT,
        }

    template_names = ["ggplot2", *templates.keys()]

    for name, template in templates.items():
        pio.templates[name] = template

    pio.templates.default = "+".join(template_names)


def parse_rgb_string(colour: str) -> tuple[int, int, int]:
    """Parse a string like so: `rgb(255, 255, 255)`.

    Equivalent to `plotly.colours.unlabel_rgb`.
    """
    return tuple(map(int, re.findall(r"(\d+)", colour)))


def unparse_rgb_tuple(colour: tuple[int, int, int]) -> str:
    """Do the opposite of the above.

    Equivalent to `plotly.colours.label_rgb`.
    """
    return f"rgb({colour[0]}, {colour[1]}, {colour[2]})"


def parse_rgba_string(colour: str) -> tuple[int, int, int, float]:
    """Parse a string like so: `rgba(255, 255, 255, 1.0)`."""
    rgba = re.findall(r"(\d*\.?\d+)", colour)
    return tuple(int(x) if x.isdigit() else float(x) for x in rgba)


def unparse_rgba_tuple(colour: tuple[int, int, int, float]) -> str:
    """Do the opposite of the above."""
    return f"rgba({colour[0]}, {colour[1]}, {colour[2]}, {colour[3]})"


def create_colour_map(groups: list, colour_scale: list[str]) -> dict:
    """Create a map of groups to colours from a plotly colour scale.

    Typical usage example:
    >>> groups = ["train", "validate", "test"]
    ... colour_scale = px.colors.sequential.Viridis
    ... colour_map = create_colour_map(groups, colour_scale)
    """
    colours = pc.sample_colorscale(colour_scale, len(groups))

    return {group: colour for group, colour in zip(groups, colours, strict=True)}
