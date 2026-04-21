from duckdb import sql
from plotly.graph_objects import Figure
import plotly.express as px
import plotly.io as pio

from sqplot import specs
from sqplot.backends.plotly import charts
from sqplot.parser import get_chart_spec
from sqplot.backends.plotly.config import apply_theme
from sqplot.backends.plotly.layout import apply_layout


def plot(sql_script: str) -> Figure:
    apply_theme()
    df = sql(sql_script).df()
    spec = get_chart_spec(sql_script)

    x_col = spec.traces[0].encoding.x if spec.traces else None

    figs = []
    active_traces: list[specs.Chart] = []
    for trace in spec.traces:
        func = getattr(charts, trace.id, None)
        if func is None:
            continue
        fig = func(df, trace)
        figs.append(fig)
        active_traces.append(trace)

    fig = _combine_figures(figs, active_traces)
    fig = apply_layout(fig, spec.layout, x_col, spec.traces)

    return fig


def _combine_figures(
    figs: list[Figure], trace_specs: list[specs.Chart] | None = None
) -> Figure:
    """Merge multiple Plotly figures into one.

    When different charts produce traces with the same legend names (e.g. two
    line charts both grouping by the same color column), their legend entries
    would collide. To fix this, we assign each chart's traces a shared
    *legend group* identified by the chart's name or y-axis column, and render
    a group title above them in the legend. `groupclick="toggleitem"` lets
    the user hide/show individual traces while the group title toggles the
    whole chart.

    Colors are also remapped so that successive charts pick different slots
    from the active colorway rather than reusing the same first-N colors.
    """
    if len(figs) == 1:
        return figs[0]

    group_labels = _build_group_labels(figs, trace_specs)
    colorway = _get_colorway()
    color_offset = 0

    combined = Figure()
    for i, fig in enumerate(figs):
        group = group_labels[i]
        for trace in fig.data:
            _remap_color(trace, color_offset, colorway)
            if group:
                _apply_legend_group(trace, group)
            combined.add_trace(trace)
        color_offset += _count_distinct_colors(fig)

    if any(group_labels):
        combined.update_layout(legend=dict(groupclick="toggleitem", tracegroupgap=10))

    return combined


def _build_group_labels(
    figs: list[Figure], trace_specs: list[specs.Chart] | None
) -> list[str | None]:
    """Return a per-chart label used to group legend entries."""
    if not trace_specs or len(trace_specs) != len(figs):
        return [None] * len(figs)

    all_names = [t.name for fig in figs for t in fig.data]
    if len(all_names) == len(set(all_names)):
        return [None] * len(figs)

    return [spec.name or spec.encoding.y for spec in trace_specs]


def _get_colorway() -> list[str]:
    """Resolve the active colorway from the current Plotly template."""
    return (
        pio.templates[pio.templates.default].layout.colorway
        or px.colors.qualitative.Plotly
    )


def _remap_color(trace, offset: int, colorway: list[str]):
    """Shift a trace's marker/line color by offset positions in the colorway."""
    if trace.type in ("histogram2dcontour", "histogram2d"):
        return

    c = getattr(trace.marker, "color", None)
    if not isinstance(c, str):
        return

    try:
        idx = colorway.index(c)
        new_color = colorway[(idx + offset) % len(colorway)]
    except ValueError:
        new_color = colorway[offset % len(colorway)]

    trace.marker.color = new_color
    if trace.type == "scatter":
        trace.line.color = new_color


def _apply_legend_group(trace, group: str):
    """Assign trace to legend group with a group title."""
    trace.legendgroup = group
    if trace.name:
        trace.legendgrouptitle = dict(text=group)


def _count_distinct_colors(fig: Figure) -> int:
    """Count distinct string marker colors across all traces in fig."""
    return len(
        {c for t in fig.data if isinstance(c := getattr(t.marker, "color", None), str)}
    )
