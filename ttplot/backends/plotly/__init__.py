from duckdb import sql
from plotly.graph_objects import Figure

from ttplot import specs
from ttplot.backends.plotly import charts
from ttplot.backends.plotly.utils import get_colorway
from ttplot.parser import get_chart_spec
from ttplot.backends.plotly.config import apply_theme
from ttplot.backends.plotly.layout import apply_layout

NO_FILLCOLOR = frozenset({"histogram", "histogram2d", "histogram2dcontour"})


def plot(sql_script: str) -> Figure:
    apply_theme()
    df = sql(sql_script).df()
    spec = get_chart_spec(sql_script)

    figs, active_traces = [], []
    for trace in spec.traces:
        func = getattr(charts, trace.id, None)
        if func:
            figs.append(func(df, trace))
            active_traces.append(trace)

    fig = _combine_figures(figs, active_traces)
    fig = apply_layout(fig, spec.layout, spec.traces)

    return fig


def _combine_figures(
    figs: list[Figure], trace_specs: list[specs.Chart] | None = None
) -> Figure:
    if len(figs) == 1:
        for t in figs[0].data:
            if (
                t.opacity is not None
                and t.type not in NO_FILLCOLOR
                and getattr(t, "fillcolor", None) is None
            ):
                c = _primary_color(t)
                if c:
                    t.fillcolor = c
        return figs[0]

    colorway = get_colorway()
    color_idx = 0
    combined = Figure()

    names = [t.name for f in figs for t in f.data]
    needs_groups = len(names) != len(set(names))

    for i, fig in enumerate(figs):
        spec = trace_specs[i] if trace_specs and i < len(trace_specs) else None
        is_multi = len(fig.data) > 1

        for trace in fig.data:
            _set_color(trace, colorway[color_idx % len(colorway)])
            color_idx += 1

            if not trace.name and spec:
                trace.name = spec.name or spec.encoding.y
            if trace.name:
                trace.showlegend = True
            if needs_groups and is_multi and spec:
                group = spec.name or spec.encoding.y
                trace.legendgroup = group
                trace.legendgrouptitle = dict(text=group)

            combined.add_trace(trace)

    if needs_groups:
        combined.update_layout(legend=dict(groupclick="toggleitem", tracegroupgap=10))

    return combined


def _primary_color(trace) -> str | None:
    """Return the first hex color from marker or line."""
    for src in (getattr(trace, "marker", None), getattr(trace, "line", None)):
        if src is not None:
            c = getattr(src, "color", None)
            # Only consider hex colors, skip RGBA colors (with alpha)
            if isinstance(c, str) and c.startswith("#"):
                return c
    return None


def _set_color(trace, color: str):
    """Assign color to marker, line, and fill."""
    trace.marker.color = color

    if hasattr(trace, "line"):
        lc = getattr(trace.line, "color", None)
        # Only consider hex colors, skip RGBA colors (with alpha)
        if lc is None or lc.startswith("#"):
            trace.line.color = color

    if trace.type in NO_FILLCOLOR:
        return

    fc = getattr(trace, "fillcolor", None)
    if fc is None:
        if trace.opacity is not None:
            trace.fillcolor = color
    elif fc.startswith("#"):
        trace.fillcolor = color