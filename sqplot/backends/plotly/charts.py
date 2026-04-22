import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqplot import specs
from .utils import (
    apply_opacity,
    border_style_update,
    build_style_maps,
    color_with_alpha,
    common_params,
    get_colorway,
    group_mask,
    has_duplicate_x,
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

    dupes = has_duplicate_x(df, x_col, color_col, y_col, style_col)

    if dupes:
        group_cols = [c for c in [x_col, color_col, style_col] if c]
        plot_df = (
            df.groupby(group_cols)
            .agg(y_mean=(y_col, "mean"), y_std=(y_col, "std"))
            .reset_index()
        )
        plot_df["y_std"] = plot_df["y_std"].fillna(0)
    else:
        plot_df = None

    fig = go.Figure()
    colorway = get_colorway()
    band_opacity = spec.error_band.opacity if spec.error_band else 0.2

    color_groups = list(df[color_col].unique()) if color_col else [None]
    style_groups = list(df[style_col].unique()) if style_col else [None]
    smaps = build_style_maps(df[style_col].unique()) if style_col else {}
    fallback = spec.name or y_col

    for ci, cv in enumerate(color_groups):
        color = colorway[ci % len(colorway)]
        for sv in style_groups:
            if dupes:
                mask = group_mask(plot_df, color_col, style_col, cv, sv)
                gdf = plot_df[mask].sort_values(x_col)
                y_data = gdf["y_mean"]
            else:
                mask = group_mask(df, color_col, style_col, cv, sv)
                gdf = df[mask]
                y_data = gdf[y_col]

            if len(gdf) == 0:
                continue

            tname = trace_name(cv, sv, fallback)
            dash, symbol = (
                smaps.get(sv, ("solid", "circle")) if style_col else ("solid", "circle")
            )

            if dupes:
                upper = y_data + gdf["y_std"]
                lower = y_data - gdf["y_std"]
                fig.add_trace(
                    go.Scatter(
                        x=pd.concat([gdf[x_col], gdf[x_col].iloc[::-1]]),
                        y=pd.concat([upper, lower.iloc[::-1]]),
                        fill="toself",
                        fillcolor=color_with_alpha(color, band_opacity),
                        line=dict(color="rgba(0,0,0,0)"),
                        hoverinfo="skip",
                        showlegend=False,
                        legendgroup=tname,
                    )
                )

            trace = go.Scatter(
                x=gdf[x_col],
                y=y_data,
                mode="lines+markers",
                name=tname,
                legendgroup=tname,
                line=dict(color=color, dash=dash),
                marker=dict(symbol=symbol, color=color),
            )
            _apply_line_spec(trace, spec, gdf)
            if style_col and dash != "solid":
                trace.line.dash = dash
            if spec.opacity is not None:
                trace.opacity = spec.opacity
            fig.add_trace(trace)

    return fig


def _apply_line_spec(trace: go.Scatter, spec: specs.Line, gdf: pd.DataFrame) -> None:
    trace.update(**line_style_update(spec.line_style))
    trace.update(**marker_style_update(spec.markers))
    if spec.error_bar:
        eb_y = spec.error_bar.y
        eb_y_minus = spec.error_bar.y_minus
        if isinstance(eb_y, str):
            trace.error_y = dict(type="data", array=gdf[eb_y].tolist(), visible=True)
        elif isinstance(eb_y, (int, float)):
            if eb_y_minus is not None:
                trace.error_y = dict(
                    type="data",
                    symmetric=False,
                    arrayminus=(
                        gdf[eb_y_minus].tolist()
                        if isinstance(eb_y_minus, str)
                        else [eb_y_minus] * len(gdf)
                    ),
                    array=[eb_y] * len(gdf),
                    visible=True,
                )
            else:
                trace.error_y = dict(
                    type="data",
                    symmetric=True,
                    array=[eb_y] * len(gdf),
                    visible=True,
                )
        elif isinstance(eb_y, list):
            trace.error_y = dict(type="data", symmetric=True, array=eb_y, visible=True)
    if spec.name:
        trace.name = spec.name
        trace.showlegend = True


def scatter(df: pd.DataFrame, spec: specs.Scatter) -> go.Figure:
    params = common_params(spec.encoding)
    if spec.encoding.style:
        params["symbol"] = spec.encoding.style
    fig = px.scatter(df, x=spec.encoding.x, y=spec.encoding.y, **params)
    update = marker_style_update(spec.markers)
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def bar(df: pd.DataFrame, spec: specs.Bar) -> go.Figure:
    params = common_params(spec.encoding) | orient_xy(spec.encoding, spec.orientation)
    fig = px.histogram(df, histfunc="avg", **params)
    update = {}
    if spec.color:
        update["marker_color"] = spec.color
    update.update(border_style_update(spec.border))
    if spec.bar_width is not None:
        update["width"] = spec.bar_width
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    if spec.annotation_position:
        update["textposition"] = spec.annotation_position
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def area(df: pd.DataFrame, spec: specs.Area) -> go.Figure:
    fig = px.area(
        df, x=spec.encoding.x, y=spec.encoding.y, **common_params(spec.encoding)
    )
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
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def box(df: pd.DataFrame, spec: specs.Box) -> go.Figure:
    params = common_params(spec.encoding) | orient_xy(spec.encoding, spec.orientation)
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
    params = common_params(spec.encoding) | orient_xy(spec.encoding, spec.orientation)
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
    params = common_params(spec.encoding) | orient_xy(spec.encoding, spec.orientation)
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
    params = common_params(spec.encoding)
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
    params = common_params(spec.encoding)
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
        return px.density_contour(
            df, x=x_col, y=spec.encoding.y, **common_params(spec.encoding)
        )

    color_col = spec.encoding.color
    rows = []
    y_col = spec.encoding.y
    if color_col:
        for group_val, group_df in df.groupby(color_col):
            x_grid, y_kde = compute_kde_1d(group_df[y_col])
            if len(x_grid) == 0:
                continue
            for x, y in zip(x_grid, y_kde):
                rows.append({y_col: x, "density": y, color_col: group_val})
    else:
        x_grid, y_kde = compute_kde_1d(df[y_col])
        for x, y in zip(x_grid, y_kde):
            rows.append({y_col: x, "density": y})
    kde_df = pd.DataFrame(rows)

    kde_params = {}
    if color_col:
        kde_params["color"] = color_col
    fig = px.area(kde_df, x=y_col, y="density", **kde_params)
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
    params = common_params(spec.encoding)
    if spec.nbinsx is not None:
        params["nbinsx"] = spec.nbinsx
    if spec.nbinsy is not None:
        params["nbinsy"] = spec.nbinsy
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
    if spec.annotation_position:
        update["textposition"] = spec.annotation_position
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
    params = common_params(spec.encoding)
    if spec.encoding.dim:
        params["dimensions"] = spec.encoding.dim
    fig = px.scatter_matrix(df, **params)
    if not spec.diagonal_visible:
        fig.update_traces(diagonal_visible=False)
    return fig


def parallel_categories(df: pd.DataFrame, spec: specs.ParallelCategories) -> go.Figure:
    params = common_params(spec.encoding)
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
    params = common_params(spec.encoding)
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
        **common_params(spec.encoding),
    )
    update = {}
    update.update(border_style_update(spec.border))
    if spec.name:
        update.update(name=spec.name, showlegend=True)
    fig.update_traces(**update)
    apply_opacity(fig, spec.opacity)
    return fig


def line_polar(df: pd.DataFrame, spec: specs.LinePolar) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    return px.line_polar(df, r=spec.encoding.y, theta=spec.encoding.x, **params)


def scatter_polar(df: pd.DataFrame, spec: specs.ScatterPolar) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    return px.scatter_polar(df, r=spec.encoding.y, theta=spec.encoding.x, **params)


def bar_polar(df: pd.DataFrame, spec: specs.BarPolar) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    fig = px.bar_polar(df, r=spec.encoding.y, theta=spec.encoding.x, **params)
    apply_opacity(fig, spec.opacity)
    return fig


def line_3d(df: pd.DataFrame, spec: specs.Line3D) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    return px.line_3d(
        df, x=spec.encoding.x, y=spec.encoding.y, z=spec.encoding.z, **params
    )


def scatter_3d(df: pd.DataFrame, spec: specs.Scatter3D) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    return px.scatter_3d(
        df, x=spec.encoding.x, y=spec.encoding.y, z=spec.encoding.z, **params
    )


def line_ternary(df: pd.DataFrame, spec: specs.LineTernary) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    return px.line_ternary(
        df, a=spec.encoding.a, b=spec.encoding.x, c=spec.encoding.y, **params
    )


def scatter_ternary(df: pd.DataFrame, spec: specs.ScatterTernary) -> go.Figure:
    params = {}
    if spec.encoding.color:
        params["color"] = spec.encoding.color
    return px.scatter_ternary(
        df, a=spec.encoding.a, b=spec.encoding.x, c=spec.encoding.y, **params
    )
