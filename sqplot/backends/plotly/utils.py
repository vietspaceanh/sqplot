import plotly.graph_objects as go
import pandas as pd
import plotly.express as px
import plotly.io as pio

from sqplot import specs

DASH_PATTERNS = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
MARKER_SYMBOLS = [
    "circle",
    "square",
    "diamond",
    "cross",
    "x",
    "triangle-up",
    "triangle-down",
]


def line_style_update(line_style: specs.LineStyle | None) -> dict:
    update = {}
    if line_style:
        if line_style.color:
            update["line_color"] = line_style.color
        if line_style.width is not None:
            update["line_width"] = line_style.width
        if line_style.dash:
            update["line_dash"] = line_style.dash
    return update


def marker_style_update(markers: specs.MarkerStyle | None) -> dict:
    update = {}
    if markers:
        if markers.color:
            update["marker_color"] = markers.color
        if markers.size is not None:
            update["marker_size"] = markers.size
        if markers.symbol:
            update["marker_symbol"] = markers.symbol
        if markers.border_color:
            update["marker_line_color"] = markers.border_color
        if markers.border_width is not None:
            update["marker_line_width"] = markers.border_width
        if markers.opacity is not None:
            update["marker_opacity"] = markers.opacity
    return update


def border_style_update(border: specs.BorderStyle | None) -> dict:
    update = {}
    if border:
        if border.color:
            update["marker_line_color"] = border.color
        if border.width is not None:
            update["marker_line_width"] = border.width
    return update


def build_style_maps(style_values) -> dict:
    vals = list(style_values)
    return {
        v: (
            DASH_PATTERNS[i % len(DASH_PATTERNS)],
            MARKER_SYMBOLS[i % len(MARKER_SYMBOLS)],
        )
        for i, v in enumerate(vals)
    }


def common_params(encoding: specs.Encoding) -> dict:
    params = {}
    if encoding.color:
        params["color"] = encoding.color
    if encoding.facet_row:
        params["facet_row"] = encoding.facet_row
        params["facet_row_spacing"] = 0.12
    if encoding.facet_col:
        params["facet_col"] = encoding.facet_col
        params["facet_col_spacing"] = 0.12
    return params


def orient_xy(encoding: specs.Encoding, orientation: str | None) -> dict:
    if orientation == "h":
        return {"x": encoding.y, "y": encoding.x, "orientation": "h"}
    return {"x": encoding.x, "y": encoding.y}


def get_colorway() -> list[str]:
    return (
        pio.templates[pio.templates.default].layout.colorway
        or px.colors.qualitative.Plotly
    )


def color_with_alpha(hex_color: str, alpha: float) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def apply_opacity(fig: go.Figure, opacity: float | None) -> None:
    if opacity is None:
        return
    fig.update_traces(marker_opacity=opacity)
    for t in fig.data:
        c = (
            getattr(t.marker, "color", None)
            or getattr(t, "marker_color", None)
            or getattr(t.line, "color", None)
        )
        if isinstance(c, str) and c.startswith("#"):
            rgba = color_with_alpha(c, opacity)
            try:
                t.fillcolor = rgba
            except ValueError:
                pass
            try:
                t.line.color = rgba
            except (ValueError, AttributeError):
                pass


def has_duplicate_x(
    df: pd.DataFrame,
    x_col: str | None,
    color_col: str | None,
    y_col: str,
    style_col: str | None = None,
) -> bool:
    if not x_col:
        return False
    group_cols = [c for c in [x_col, color_col, style_col] if c]
    return df.groupby(group_cols)[y_col].count().gt(1).any()


def group_mask(
    data: pd.DataFrame,
    color_col: str | None,
    style_col: str | None,
    cv,
    sv,
) -> pd.Series:
    mask = pd.Series(True, index=data.index)
    if cv is not None:
        mask &= data[color_col] == cv
    if sv is not None:
        mask &= data[style_col] == sv
    return mask


def trace_name(cv, sv, fallback: str) -> str:
    if cv is not None and sv is not None:
        return f"{cv} ({sv})"
    if cv is not None:
        return str(cv)
    if sv is not None:
        return str(sv)
    return fallback
