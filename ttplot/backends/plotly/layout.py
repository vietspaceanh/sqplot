import plotly.graph_objects as go

from ttplot.specs import (
    Layout,
    Density,
    Text,
    XLine,
    YLine,
    XRect,
    YRect,
    Rect,
)

STANDARD_XY = {"line", "scatter", "area", "box", "violin", "strip"}
_DEFAULT_RECT_FILL = "yellow"
_DEFAULT_RECT_ALPHA = 0.4


def apply_layout(fig: go.Figure, layout: Layout, traces: list) -> go.Figure:
    _apply_base_layout(fig, layout)
    _apply_axes(fig, layout, traces)
    _apply_axis_labels(fig, layout, traces)
    _apply_noerror(fig, layout)
    _apply_shapes(fig, layout)
    return fig


def _apply_base_layout(fig: go.Figure, layout: Layout) -> None:
    layout_update = {}
    if layout.title is not None:
        layout_update["title"] = layout.title
    if layout.width is not None:
        layout_update["width"] = layout.width
    if layout.height is not None:
        layout_update["height"] = layout.height
    if layout.xlabel is not None:
        layout_update["xaxis_title"] = layout.xlabel
    if layout.ylabel is not None:
        layout_update["yaxis_title"] = layout.ylabel
    if layout.barmode is not None:
        layout_update["barmode"] = layout.barmode
    if layout.legend is not None:
        layout_update["showlegend"] = layout.legend
    if layout.legend_horizontal:
        layout_update["legend"] = layout_update.get("legend", {})
        if isinstance(layout_update.get("legend"), dict):
            layout_update["legend"]["orientation"] = "h"
    if layout_update:
        fig.update_layout(**layout_update)


def _apply_axes(fig: go.Figure, layout: Layout, traces: list) -> None:
    if layout.grid is not None:
        fig.update_xaxes(showgrid=layout.grid)
        fig.update_yaxes(showgrid=layout.grid)
    if layout.xgrid is not None:
        fig.update_xaxes(showgrid=layout.xgrid)
    if layout.ygrid is not None:
        fig.update_yaxes(showgrid=layout.ygrid)

    if layout.x_range is not None:
        fig.update_xaxes(range=layout.x_range)
    else:
        fig.update_xaxes(autorange=True)
    if layout.y_range is not None:
        fig.update_yaxes(range=layout.y_range)
    else:
        fig.update_yaxes(autorange=True)


def _visual_axes(traces: list) -> tuple[str | None, str | None]:
    if not traces:
        return None, None
    t = traces[0]
    orient = getattr(t, "orientation", None)
    if orient == "h":
        return t.encoding.y, t.encoding.x
    return t.encoding.x, t.encoding.y


def _apply_axis_labels(fig: go.Figure, layout: Layout, traces: list) -> None:
    vx, vy = _visual_axes(traces)
    agg = getattr(fig, "_ttplot_agg", False)
    y_col = traces[0].encoding.y if traces else None

    if layout.xlabel is None:
        if vx:
            title = f"avg of {vx}" if agg and vx == y_col else vx
            fig.update_xaxes(title=title)
        elif len(traces) == 1:
            t = traces[0]
            if isinstance(t, Density) and t.encoding.x is None:
                fig.update_xaxes(title=t.encoding.y)

    if layout.ylabel is None:
        if len(traces) == 1:
            t = traces[0]
            if type(t).__name__.lower().replace("_", " ") in STANDARD_XY or (
                isinstance(t, Density) and vx
            ):
                if getattr(t, "orientation", None) == "h":
                    if t.encoding.x:
                        fig.update_yaxes(title=t.encoding.x)
                else:
                    if t.encoding.y:
                        fig.update_yaxes(title=t.encoding.y)
        elif len(traces) > 1:
            y_cols = {
                t.encoding.y for t in traces if hasattr(t, "encoding") and t.encoding.y
            }
            if len(y_cols) > 1:
                fig.update_yaxes(title="")


def _apply_noerror(fig: go.Figure, layout: Layout) -> None:
    if not layout.noerror:
        return
    for trace in fig.data:
        if hasattr(trace, "error_x") and trace.error_x is not None:
            trace.error_x = None
        if hasattr(trace, "error_y") and trace.error_y is not None:
            trace.error_y = None


def _apply_shapes(fig: go.Figure, layout: Layout) -> None:
    for shape in layout.shapes:
        if isinstance(shape, Text):
            _render_text(fig, shape)
        elif isinstance(shape, XLine):
            _render_xline(fig, shape)
        elif isinstance(shape, YLine):
            _render_yline(fig, shape)
        elif isinstance(shape, XRect):
            _render_xrect(fig, shape)
        elif isinstance(shape, YRect):
            _render_yrect(fig, shape)
        elif isinstance(shape, Rect):
            _render_rect(fig, shape)


def _render_text(fig: go.Figure, s: Text) -> None:
    params: dict = {"text": s.text, "showarrow": s.showarrow, "arrowhead": 3}
    if s.x is not None:
        params["x"] = s.x
    if s.y is not None:
        params["y"] = s.y
    font = {}
    if s.color is not None:
        font["color"] = s.color
    if s.size is not None:
        font["size"] = s.size
    if font:
        params["font"] = font
    if s.color is not None:
        params["arrowcolor"] = s.color
    fig.add_annotation(**params)


def _render_xline(fig: go.Figure, s: XLine) -> None:
    params: dict = {"x": s.loc}
    if s.color:
        params["line_color"] = s.color
    if s.size is not None:
        params["line_width"] = s.size
    if s.dash:
        params["line_dash"] = s.dash
    if s.alpha is not None:
        params["opacity"] = s.alpha
    if s.text:
        params["annotation_text"] = s.text
    fig.add_vline(**params)


def _render_yline(fig: go.Figure, s: YLine) -> None:
    params: dict = {"y": s.loc}
    if s.color:
        params["line_color"] = s.color
    if s.size is not None:
        params["line_width"] = s.size
    if s.dash:
        params["line_dash"] = s.dash
    if s.alpha is not None:
        params["opacity"] = s.alpha
    if s.text:
        params["annotation_text"] = s.text
    fig.add_hline(**params)


def _render_xrect(fig: go.Figure, s: XRect) -> None:
    fig.add_vrect(
        x0=s.x0,
        x1=s.x1,
        fillcolor=s.color or _DEFAULT_RECT_FILL,
        opacity=s.alpha if s.alpha is not None else _DEFAULT_RECT_ALPHA,
        line_width=0,
    )


def _render_yrect(fig: go.Figure, s: YRect) -> None:
    fig.add_hrect(
        y0=s.y0,
        y1=s.y1,
        fillcolor=s.color or _DEFAULT_RECT_FILL,
        opacity=s.alpha if s.alpha is not None else _DEFAULT_RECT_ALPHA,
        line_width=0,
    )


def _render_rect(fig: go.Figure, s: Rect) -> None:
    fig.add_shape(
        type="rect",
        x0=s.x0,
        x1=s.x1,
        y0=s.y0,
        y1=s.y1,
        fillcolor=s.color or _DEFAULT_RECT_FILL,
        opacity=s.alpha if s.alpha is not None else _DEFAULT_RECT_ALPHA,
        line_width=0,
    )
