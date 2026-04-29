import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ttplot import specs
from .utils import (
    apply_opacity,
    border_style_update,
    build_style_maps,
    color_with_alpha,
    common_params,
    dim_cols,
    get_colorway,
    group_mask,
    has_duplicates,
    label_template,
    line_style_update,
    marker_style_update,
    orient_xy,
    trace_name,
)


def line(df: pd.DataFrame, spec: specs.Line) -> go.Figure:
    x_col = spec.encoding.x
    y_col = spec.encoding.y
    color_col = spec.encoding.color
    style_col = spec.encoding.style

    dupes = has_duplicates(df, spec)

    if dupes:
        std_col = "__line_std__"
        gc = dim_cols(spec)
        agg_df = (
            df.groupby(gc)
            .agg(**{y_col: (y_col, "mean"), std_col: (y_col, "std")})
            .reset_index()
        )
        agg_df[std_col] = agg_df[std_col].fillna(0)
    else:
        agg_df = None

    params = common_params(spec)
    fig = px.line(agg_df if dupes else df, x=x_col, y=y_col, **params)

    has_user_band = spec.error_band and spec.error_band.lower is not None

    if dupes and not has_user_band:
        band_opacity = spec.error_band.opacity if spec.error_band else 0.2

        for trace in list(fig.data):
            trace_df = pd.DataFrame({x_col: trace.x, y_col: trace.y})
            matched = trace_df.merge(
                agg_df[[x_col, y_col, std_col]], on=[x_col, y_col]
            ).sort_values(x_col)

            if matched.empty:
                continue

            upper = matched[y_col] + matched[std_col]
            lower = matched[y_col] - matched[std_col]
            line_color = getattr(trace.line, "color", None) or get_colorway()[0]

            fig.add_trace(
                go.Scatter(
                    x=pd.concat([matched[x_col], matched[x_col].iloc[::-1]]),
                    y=pd.concat([upper, lower.iloc[::-1]]),
                    fill="toself",
                    fillcolor=color_with_alpha(line_color, band_opacity),
                    line=dict(color="rgba(0,0,0,0)"),
                    hoverinfo="skip",
                    showlegend=False,
                    legendgroup=trace.legendgroup,
                    xaxis=trace.xaxis,
                    yaxis=trace.yaxis,
                )
            )

    if has_user_band:
        _apply_error_band(fig, spec, df, x_col, y_col, agg_df if dupes else None)

    if spec.markers is False:
        base_mode = "lines"
    else:
        base_mode = "lines+markers"
    label_upd = label_template(spec, dupes=dupes)
    if label_upd:
        base_mode += "+text"
    fig.update_traces(mode=base_mode)
    update = {}
    update.update(**line_style_update(spec.line_style))
    update.update(**marker_style_update(spec.markers))
    if spec.opacity is not None:
        update["opacity"] = spec.opacity
    if label_upd:
        update.update(label_upd)
    fig.update_traces(**update)

    if spec.name:
        fig.update_traces(name=spec.name, showlegend=True)

    return fig


def _compute_band_bounds(
    data: pd.DataFrame, y_col: str, lower: str | float, upper: str | float
) -> tuple[pd.Series, pd.Series]:
    lo = data[lower] if isinstance(lower, str) else data[y_col] - lower
    hi = data[upper] if isinstance(upper, str) else data[y_col] + upper
    if isinstance(lower, str) and isinstance(upper, str) and lower == upper:
        lo = data[y_col] - data[lower]
        hi = data[y_col] + data[upper]
    return lo, hi


def _apply_error_band(
    fig: go.Figure,
    spec: specs.Line,
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    agg_df: pd.DataFrame | None,
) -> None:
    eb = spec.error_band
    band_opacity = eb.opacity
    data = agg_df if agg_df is not None else df

    for trace in list(fig.data):
        n = len(trace.x) if hasattr(trace, "x") and trace.x is not None else 0
        if n == 0:
            continue

        lo_vals, hi_vals = _compute_band_bounds(data, y_col, eb.lower, eb.upper)

        trace_df = pd.DataFrame({x_col: trace.x, y_col: trace.y})
        if agg_df is not None:
            std_col = "__line_std__"
            merge_cols = [c for c in [x_col, y_col, std_col] if c in agg_df.columns]
            matched = trace_df.merge(agg_df[merge_cols], on=[x_col, y_col]).sort_values(
                x_col
            )
        else:
            matched = trace_df.merge(
                data[[x_col, y_col]], on=[x_col, y_col]
            ).sort_values(x_col)

        if matched.empty:
            continue

        idx = matched.index[:n]
        lower = lo_vals.loc[idx].reset_index(drop=True)
        upper = hi_vals.loc[idx].reset_index(drop=True)

        line_color = getattr(trace.line, "color", None) or get_colorway()[0]

        fig.add_trace(
            go.Scatter(
                x=pd.concat(
                    [
                        matched[x_col].reset_index(drop=True),
                        matched[x_col].reset_index(drop=True).iloc[::-1],
                    ]
                ),
                y=pd.concat([upper, lower.iloc[::-1]]),
                fill="toself",
                fillcolor=color_with_alpha(line_color, band_opacity),
                line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip",
                showlegend=False,
                legendgroup=trace.legendgroup,
                xaxis=trace.xaxis,
                yaxis=trace.yaxis,
            )
        )


def scatter(df: pd.DataFrame, spec: specs.Scatter) -> go.Figure:
    params = common_params(spec)
    fig = px.scatter(df, x=spec.encoding.x, y=spec.encoding.y, **params)
    update = marker_style_update(spec.markers)
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    label_upd = label_template(spec)
    if label_upd:
        update["mode"] = "markers+text"
        update.update(label_upd)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def bar(df: pd.DataFrame, spec: specs.Bar) -> go.Figure:
    y_col = spec.encoding.y
    dupes = has_duplicates(df, spec)
    params = common_params(spec) | orient_xy(spec.encoding, spec.orientation)

    if dupes:
        std_col = "__bar_std__"
        agg_df = (
            df.groupby(dim_cols(spec))
            .agg(**{y_col: (y_col, "mean"), std_col: (y_col, "std")})
            .reset_index()
        )
        agg_df[std_col] = agg_df[std_col].fillna(0)
        err_key = "error_x" if spec.orientation == "h" else "error_y"
        params[err_key] = std_col
        fig = px.bar(agg_df, **params)
        fig._ttplot_agg = True
    else:
        fig = px.bar(df, **params)

    update = {}
    if spec.color:
        update["marker_color"] = spec.color
    update.update(border_style_update(spec.border))
    if spec.bar_width is not None:
        update["width"] = spec.bar_width
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    label_upd = label_template(spec, dupes=dupes)
    if label_upd:
        update.update(label_upd)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def area(df: pd.DataFrame, spec: specs.Area) -> go.Figure:
    fig = px.area(df, x=spec.encoding.x, y=spec.encoding.y, **common_params(spec))
    update = {}
    if spec.fill_color:
        update["fillcolor"] = spec.fill_color
    update.update(line_style_update(spec.line_style))
    if spec.markers:
        mu = {}
        if spec.markers.color:
            mu["marker_color"] = spec.markers.color
        if spec.markers.size is not None:
            mu["marker_size"] = spec.markers.size
        if spec.markers.symbol:
            mu["marker_symbol"] = spec.markers.symbol
        update.update(mu)
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    label_upd = label_template(spec)
    if label_upd:
        update["mode"] = "lines+markers+text" if spec.markers else "lines+text"
        update.update(label_upd)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def box(df: pd.DataFrame, spec: specs.Box) -> go.Figure:
    params = common_params(spec) | orient_xy(spec.encoding, spec.orientation)
    fig = px.box(df, **params)
    update = {}
    if spec.marker_color:
        update["marker_color"] = spec.marker_color
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def violin(df: pd.DataFrame, spec: specs.Violin) -> go.Figure:
    params = common_params(spec) | orient_xy(spec.encoding, spec.orientation)
    if spec.box:
        params["box"] = True
    if spec.points:
        params["points"] = spec.points
    if spec.side:
        params["side"] = spec.side
    fig = px.violin(df, **params)
    update = {}
    if spec.marker_color:
        update["marker_color"] = spec.marker_color
    if spec.mean_line:
        update["meanline_visible"] = True
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def strip(df: pd.DataFrame, spec: specs.Strip) -> go.Figure:
    params = common_params(spec) | orient_xy(spec.encoding, spec.orientation)
    fig = px.strip(df, **params)
    update = {}
    if spec.markers:
        if spec.markers.color:
            update["marker_color"] = spec.markers.color
        if spec.markers.opacity is not None:
            update["marker_opacity"] = spec.markers.opacity
    if spec.jitter is not None:
        update["jitter"] = spec.jitter
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    return fig


def hist(df: pd.DataFrame, spec: specs.Hist) -> go.Figure:
    params = common_params(spec)
    if spec.nbins is not None:
        params["nbins"] = spec.nbins
    if spec.orientation == "h":
        params["orientation"] = "h"
        fig = px.histogram(df, y=spec.encoding.y, **params)
    else:
        fig = px.histogram(df, x=spec.encoding.y, **params)
    update = {"marker_line_width": 1}
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def ecdf(df: pd.DataFrame, spec: specs.ECDF) -> go.Figure:
    params = common_params(spec)
    if spec.complementary:
        params["complementary"] = True
    if not spec.lines:
        params["lines"] = False
    if spec.markers:
        params["markers"] = True
    fig = px.ecdf(df, x=spec.encoding.y, **params)
    apply_opacity(fig, spec.opacity)
    return fig


def density(df: pd.DataFrame, spec: specs.Density) -> go.Figure:

    def compute_kde_1d(data, grid_size=200):
        data = data.dropna().values
        if len(data) < 2:
            return np.array([]), np.array([])
        bandwidth = 1.06 * np.std(data, ddof=1) * len(data) ** (-1 / 5)
        if bandwidth == 0:
            return np.array([]), np.array([])
        x_min, x_max = data.min(), data.max()
        padding = (x_max - x_min) * 0.1
        x_grid = np.linspace(x_min - padding, x_max + padding, grid_size)
        diff = x_grid[:, None] - data[None, :]
        y_kde = np.exp(-0.5 * (diff / bandwidth) ** 2).sum(axis=1) / (
            len(data) * bandwidth * np.sqrt(2 * np.pi)
        )
        return x_grid, y_kde

    x_col = spec.encoding.x
    if x_col:
        return px.density_contour(df, x=x_col, y=spec.encoding.y, **common_params(spec))

    color_col = spec.encoding.color
    facet_row_col = spec.encoding.facet_row
    facet_col_col = spec.encoding.facet_col
    group_cols = [c for c in [color_col, facet_row_col, facet_col_col] if c]

    rows = []
    y_col = spec.encoding.y
    if group_cols:
        for vals, group_df in df.groupby(group_cols):
            x_grid, y_kde = compute_kde_1d(group_df[y_col])
            if len(x_grid) == 0:
                continue
            if not isinstance(vals, tuple):
                vals = (vals,)
            for x, y in zip(x_grid, y_kde):
                row = {y_col: x, "density": y}
                row.update(zip(group_cols, vals))
                rows.append(row)
    else:
        x_grid, y_kde = compute_kde_1d(df[y_col])
        for x, y in zip(x_grid, y_kde):
            rows.append({y_col: x, "density": y})
    kde_df = pd.DataFrame(rows)

    fig = px.area(kde_df, x=y_col, y="density", **common_params(spec))
    for t in fig.data:
        t.stackgroup = None
        t.fill = "tozeroy"
    apply_opacity(fig, spec.opacity)

    update = line_style_update(spec.line_style)
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    if update:
        fig.update_traces(**update)
    return fig


def heatmap(df: pd.DataFrame, spec: specs.Heatmap) -> go.Figure:
    params = common_params(spec)
    params["nbinsx"] = spec.nbinsx
    params["nbinsy"] = spec.nbinsy
    params["text_auto"] = spec.numbered
    return px.density_heatmap(df, x=spec.encoding.x, y=spec.encoding.y, **params)


def pie(df: pd.DataFrame, spec: specs.Pie) -> go.Figure:
    fig = px.pie(df, names=spec.encoding.names, values=spec.encoding.values)
    fig.update_traces(sort=spec.sort)
    apply_opacity(fig, spec.opacity)
    return fig


def funnel(df: pd.DataFrame, spec: specs.Funnel) -> go.Figure:
    fig = px.funnel(df, x=spec.encoding.y, y=spec.encoding.x)
    update = {}
    update.update(border_style_update(spec.border))
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    label_upd = label_template(spec)
    if label_upd:
        update.update(label_upd)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def funnel_area(df: pd.DataFrame, spec: specs.FunnelArea) -> go.Figure:
    params = {}
    if spec.text_info:
        params["textinfo"] = spec.text_info
    fig = px.funnel_area(
        df, names=spec.encoding.names, values=spec.encoding.values, **params
    )
    apply_opacity(fig, spec.opacity)
    return fig


def treemap(df: pd.DataFrame, spec: specs.Treemap) -> go.Figure:
    params = {
        "names": spec.encoding.names,
        "values": spec.encoding.values,
        "parents": spec.encoding.parents,
    }
    if spec.maxdepth is not None:
        params["maxdepth"] = spec.maxdepth
    fig = px.treemap(df, **params)
    update = {}
    if spec.branchvalues:
        update["branchvalues"] = spec.branchvalues
    if update:
        fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def sunburst(df: pd.DataFrame, spec: specs.Sunburst) -> go.Figure:
    params = {
        "names": spec.encoding.names,
        "values": spec.encoding.values,
        "parents": spec.encoding.parents,
    }
    if spec.maxdepth is not None:
        params["maxdepth"] = spec.maxdepth
    fig = px.sunburst(df, **params)
    update = {}
    if spec.branchvalues:
        update["branchvalues"] = spec.branchvalues
    if update:
        fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def icicle(df: pd.DataFrame, spec: specs.Icicle) -> go.Figure:
    params = {
        "names": spec.encoding.names,
        "values": spec.encoding.values,
        "parents": spec.encoding.parents,
    }
    if spec.maxdepth is not None:
        params["maxdepth"] = spec.maxdepth
    fig = px.icicle(df, **params)
    update = {}
    if spec.branchvalues:
        update["branchvalues"] = spec.branchvalues
    if update:
        fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def scatter_matrix(df: pd.DataFrame, spec: specs.ScatterMatrix) -> go.Figure:
    params = common_params(spec)
    if spec.encoding.dim:
        params["dimensions"] = spec.encoding.dim
    fig = px.scatter_matrix(df, **params)
    if not spec.diagonal_visible:
        fig.update_traces(diagonal_visible=False)
    return fig


def parallel_categories(df: pd.DataFrame, spec: specs.ParallelCategories) -> go.Figure:
    params = common_params(spec)
    if spec.encoding.dim:
        params["dimensions"] = spec.encoding.dim
    fig = px.parallel_categories(df, **params)
    update = {}
    if spec.line_color:
        update["line_color"] = spec.line_color
    if spec.line_shape:
        update["line_shape"] = spec.line_shape
    if update:
        fig.update_traces(**update)
    return fig


def parallel_coordinates(
    df: pd.DataFrame, spec: specs.ParallelCoordinates
) -> go.Figure:
    params = common_params(spec)
    if spec.encoding.dim:
        params["dimensions"] = spec.encoding.dim
    fig = px.parallel_coordinates(df, **params)
    update = {}
    if spec.line_color:
        update["line_color"] = spec.line_color
    if spec.line_shape:
        update["line_shape"] = spec.line_shape
    if update:
        fig.update_traces(**update)
    return fig


def timeline(df: pd.DataFrame, spec: specs.Timeline) -> go.Figure:
    fig = px.timeline(
        df,
        x_start=spec.encoding.start,
        x_end=spec.encoding.end,
        y=spec.encoding.y,
        **common_params(spec),
    )
    update = {}
    update.update(border_style_update(spec.border))
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def line_polar(df: pd.DataFrame, spec: specs.LinePolar) -> go.Figure:
    return px.line_polar(
        df, r=spec.encoding.y, theta=spec.encoding.x, **common_params(spec)
    )


def scatter_polar(df: pd.DataFrame, spec: specs.ScatterPolar) -> go.Figure:
    return px.scatter_polar(
        df, r=spec.encoding.y, theta=spec.encoding.x, **common_params(spec)
    )


def bar_polar(df: pd.DataFrame, spec: specs.BarPolar) -> go.Figure:
    fig = px.bar_polar(
        df, r=spec.encoding.y, theta=spec.encoding.x, **common_params(spec)
    )
    apply_opacity(fig, spec.opacity)
    return fig


def line_3d(df: pd.DataFrame, spec: specs.Line3D) -> go.Figure:
    return px.line_3d(
        df,
        x=spec.encoding.x,
        y=spec.encoding.y,
        z=spec.encoding.z,
        **common_params(spec),
    )


def scatter_3d(df: pd.DataFrame, spec: specs.Scatter3D) -> go.Figure:
    return px.scatter_3d(
        df,
        x=spec.encoding.x,
        y=spec.encoding.y,
        z=spec.encoding.z,
        **common_params(spec),
    )


def line_ternary(df: pd.DataFrame, spec: specs.LineTernary) -> go.Figure:
    return px.line_ternary(
        df,
        a=spec.encoding.a,
        b=spec.encoding.x,
        c=spec.encoding.y,
        **common_params(spec),
    )


def scatter_ternary(df: pd.DataFrame, spec: specs.ScatterTernary) -> go.Figure:
    return px.scatter_ternary(
        df,
        a=spec.encoding.a,
        b=spec.encoding.x,
        c=spec.encoding.y,
        **common_params(spec),
    )
