from plotly.graph_objects import Figure
from sqplot import specs


def plot(sql_script: str) -> Figure:
    from duckdb import sql
    from sqplot.backends.plotly import charts
    from sqplot.parser import get_chart_spec
    from sqplot.backends.plotly.config import apply_theme
    from sqplot.backends.plotly.layout import apply_layout

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
    import plotly.express as px
    import plotly.io as pio

    if len(figs) == 1:
        return figs[0]

    combined = Figure(figs[0])

    colorway = (
        pio.templates[pio.templates.default].layout.colorway
        or px.colors.qualitative.Plotly
    )

    _rename = False
    if trace_specs and len(trace_specs) == len(figs):
        all_names = [t.name for fig in figs for t in fig.data]
        _rename = len(all_names) != len(set(all_names))

    if _rename:
        label = trace_specs[0].name or trace_specs[0].encoding.y
        if label:
            for trace in combined.data:
                if trace.name:
                    trace.legendgroup = label
                    trace.name = f"{label} ({trace.name})"

    offset = len(
        {
            c
            for t in figs[0].data
            if isinstance(c := getattr(t.marker, "color", None), str)
        }
    )

    for fig_idx, fig in enumerate(figs[1:], start=1):
        for trace in fig.data:
            if trace.type not in ("histogram2dcontour", "histogram2d"):
                c = getattr(trace.marker, "color", None)
                if isinstance(c, str):
                    try:
                        idx = colorway.index(c)
                        new_color = colorway[(idx + offset) % len(colorway)]
                    except ValueError:
                        new_color = colorway[offset % len(colorway)]
                    trace.marker.color = new_color
                    if trace.type == "scatter":
                        trace.line.color = new_color
            if _rename:
                label = trace_specs[fig_idx].name or trace_specs[fig_idx].encoding.y
                if label and trace.name:
                    trace.legendgroup = label
                    trace.name = f"{label} ({trace.name})"
            combined.add_trace(trace)
        offset += len(
            {
                c
                for t in fig.data
                if isinstance(c := getattr(t.marker, "color", None), str)
            }
        )

    if _rename:
        combined.update_layout(legend_tracegroupgap=10)

    return combined