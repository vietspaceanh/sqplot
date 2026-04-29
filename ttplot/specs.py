from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import ClassVar, Literal

from .roles import get_tag_value, parse_tag


# ── Data Dimension Mapping ───────────────────────────────────────────────────


@dataclass
class Encoding:
    # Cartesian coordinates
    x: str | None = None
    y: str | None = None
    z: str | None = None

    # Visual channels
    color: str | None = None
    size: str | None = None
    style: str | None = None

    facet_row: str | None = None
    facet_col: str | None = None

    # Polar coordinates (LinePolar, ScatterPolar, BarPolar)
    r: str | None = None
    theta: str | None = None

    # Ternary coordinates (LineTernary, ScatterTernary)
    a: str | None = None
    b: str | None = None
    c: str | None = None

    # Timeline interval (Timeline)
    start: str | None = None
    end: str | None = None

    # Named/hierarchical values (Pie, Funnel, Treemap, Sunburst, Icicle)
    names: str | None = None
    values: str | None = None
    parents: str | None = None

    # Multi-dimensional features (ScatterMatrix, ParallelCoordinates, ParallelCategories)
    dim: list[str] = field(default_factory=list)


# ── Aspect Classes (visual styling) ──────────────────────────────────────────


@dataclass
class LineStyle:
    color: str | None = None
    width: float | None = None
    dash: str | None = None


@dataclass
class MarkerStyle:
    color: str | None = None
    size: float | None = None
    symbol: str | None = None
    border_color: str | None = None
    border_width: float | None = None
    opacity: float | None = None


@dataclass
class BorderStyle:
    color: str | None = None
    width: float | None = None


@dataclass
class ErrorBand:
    lower: str | float | None = None
    upper: str | float | None = None
    opacity: float = 0.2


@dataclass
class Label:
    position: str = "auto"
    format: str | None = None
    col: str | None = None
    align: str | None = None


# ── Parse helpers ─────────────────────────────────────────────────────────────

BOOL_TAGS = frozenset(
    {"stacked", "grouped", "horizontal", "dashed", "dotted", "numbered", "noerror"}
)


def _get_name(tags: list[str], prefix: str) -> str | None:
    return get_tag_value(f"{prefix} name", tags, bool_tags=BOOL_TAGS)


def _get_orientation(tags: list[str], chart_id: str) -> str | None:
    if get_tag_value(f"{chart_id} horizontal", tags, bool_tags=BOOL_TAGS):
        return "h"
    return None


def _get_opacity(tags: list[str], chart_id: str) -> float | None:
    for tag in tags:
        if "=" not in tag:
            continue
        key, val = parse_tag(tag)
        if key in ("alpha", "opacity") and val is not None:
            return float(val)
    return None


def _parse_line_style(tags: list[str], prefix: str) -> LineStyle | None:
    color = get_tag_value(f"{prefix} color", tags, bool_tags=BOOL_TAGS)
    width = get_tag_value(f"{prefix} size", tags, bool_tags=BOOL_TAGS)
    dash = get_tag_value(f"{prefix} dash", tags, bool_tags=BOOL_TAGS)
    if get_tag_value(f"{prefix} dashed", tags, bool_tags=BOOL_TAGS):
        dash = "dash"
    if get_tag_value(f"{prefix} dotted", tags, bool_tags=BOOL_TAGS):
        dash = "dot"
    if any(v is not None for v in [color, width, dash]):
        return LineStyle(color=color, width=width, dash=dash)
    return None


def _parse_markers(tags: list[str], prefix: str) -> MarkerStyle | Literal[False] | None:
    val = get_tag_value(f"{prefix} markers", tags, bool_tags=BOOL_TAGS)
    if val is False:
        return False
    if not val:
        return None
    mc = get_tag_value(f"{prefix} markers color", tags, bool_tags=BOOL_TAGS)
    ms = get_tag_value(f"{prefix} markers size", tags, bool_tags=BOOL_TAGS)
    msh = get_tag_value(f"{prefix} markers shape", tags, bool_tags=BOOL_TAGS)
    mbc = get_tag_value(f"{prefix} markers border color", tags, bool_tags=BOOL_TAGS)
    mbw = get_tag_value(f"{prefix} markers border size", tags, bool_tags=BOOL_TAGS)
    return MarkerStyle(
        color=mc, size=ms, symbol=msh, border_color=mbc, border_width=mbw
    )


def _parse_border(tags: list[str], prefix: str) -> BorderStyle | None:
    bc = get_tag_value(f"{prefix} border color", tags, bool_tags=BOOL_TAGS)
    bw = get_tag_value(f"{prefix} border size", tags, bool_tags=BOOL_TAGS)
    if bc is not None or bw is not None:
        return BorderStyle(color=bc, width=bw)
    return None


def _parse_error_band(tags: list[str], prefix: str) -> ErrorBand | None:
    val = get_tag_value(f"{prefix} error", tags, bool_tags=BOOL_TAGS)
    if val is None:
        return None
    if isinstance(val, list):
        return ErrorBand(lower=val[0], upper=val[1] if len(val) > 1 else val[0])
    return ErrorBand(lower=val, upper=val)


def _parse_label(tags: list[str], prefix: str) -> Label | None:
    val = get_tag_value(f"{prefix} label", tags, bool_tags=BOOL_TAGS)
    if not val:
        return None
    col = val if isinstance(val, str) else None
    position = (
        get_tag_value(f"{prefix} label position", tags, bool_tags=BOOL_TAGS) or "auto"
    )
    fmt = get_tag_value(f"{prefix} label format", tags, bool_tags=BOOL_TAGS)
    align = get_tag_value(f"{prefix} label align", tags, bool_tags=BOOL_TAGS)
    return Label(position=position, format=fmt, col=col, align=align)


def _parse_scatter_markers(tags: list[str], prefix: str) -> MarkerStyle | None:
    mc = get_tag_value(f"{prefix} color", tags, bool_tags=BOOL_TAGS)
    ms = get_tag_value(f"{prefix} size", tags, bool_tags=BOOL_TAGS)
    msh = get_tag_value(f"{prefix} symbol", tags, bool_tags=BOOL_TAGS)
    mo = get_tag_value(f"{prefix} opacity", tags, bool_tags=BOOL_TAGS)
    if any(v is not None for v in [mc, ms, msh, mo]):
        return MarkerStyle(color=mc, size=ms, symbol=msh, opacity=mo)
    return None


# ── Chart base class ──────────────────────────────────────────────────────────


@dataclass
class Chart:
    encoding: Encoding
    name: str | None = None

    @classmethod
    def build(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if v is not None})


# ── XY Family ────────────────────────────────────────────────────────────────
# encoding.x, encoding.y, optionally encoding.color


@dataclass
class Line(Chart):
    id: ClassVar[str] = "line"
    line_style: LineStyle | None = None
    markers: MarkerStyle | Literal[False] | None = None
    error_band: ErrorBand | None = None
    opacity: float | None = None
    label: Label | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Line:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            line_style=_parse_line_style(tags, chart_id),
            markers=_parse_markers(tags, chart_id),
            error_band=_parse_error_band(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
            label=_parse_label(tags, chart_id),
        )


@dataclass
class Scatter(Chart):
    id: ClassVar[str] = "scatter"
    markers: MarkerStyle | None = None
    opacity: float | None = None
    label: Label | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Scatter:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            markers=_parse_scatter_markers(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
            label=_parse_label(tags, chart_id),
        )


@dataclass
class Bar(Chart):
    id: ClassVar[str] = "bar"
    color: str | None = None
    border: BorderStyle | None = None
    orientation: str | None = None
    bar_width: float | None = None
    opacity: float | None = None
    label: Label | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Bar:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            color=get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS),
            border=_parse_border(tags, chart_id),
            orientation=_get_orientation(tags, chart_id),
            bar_width=get_tag_value(f"{chart_id} size", tags, bool_tags=BOOL_TAGS),
            opacity=_get_opacity(tags, chart_id),
            label=_parse_label(tags, chart_id),
        )


@dataclass
class Area(Chart):
    id: ClassVar[str] = "area"
    fill_color: str | None = None
    line_style: LineStyle | None = None
    markers: MarkerStyle | None = None
    opacity: float | None = None
    label: Label | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Area:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            fill_color=get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS),
            line_style=_parse_line_style(tags, f"{chart_id} line"),
            markers=_parse_markers(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
            label=_parse_label(tags, chart_id),
        )


@dataclass
class Box(Chart):
    id: ClassVar[str] = "box"
    marker_color: str | None = None
    orientation: str | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Box:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            marker_color=get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS),
            orientation=_get_orientation(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
        )


@dataclass
class Violin(Chart):
    id: ClassVar[str] = "violin"
    marker_color: str | None = None
    box: bool = False
    points: str | None = None
    side: str | None = None
    mean_line: bool = False
    opacity: float | None = None
    orientation: str | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Violin:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            marker_color=get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS),
            box=get_tag_value(f"{chart_id} box", tags, bool_tags=BOOL_TAGS),
            points=get_tag_value(f"{chart_id} points", tags, bool_tags=BOOL_TAGS),
            side=get_tag_value(f"{chart_id} side", tags, bool_tags=BOOL_TAGS),
            mean_line=get_tag_value(f"{chart_id} mean line", tags, bool_tags=BOOL_TAGS),
            opacity=_get_opacity(tags, chart_id),
            orientation=_get_orientation(tags, chart_id),
        )


@dataclass
class Strip(Chart):
    id: ClassVar[str] = "strip"
    markers: MarkerStyle | None = None
    jitter: float | None = None
    orientation: str | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Strip:
        mc = get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS)
        mo = _get_opacity(tags, chart_id)
        markers = None
        if mc is not None or mo is not None:
            markers = MarkerStyle(color=mc, opacity=mo)
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            markers=markers,
            jitter=get_tag_value(f"{chart_id} jitter", tags, bool_tags=BOOL_TAGS),
            orientation=_get_orientation(tags, chart_id),
        )


@dataclass
class Point(Chart):
    id: ClassVar[str] = "point"
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Point:
        mc = get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS)
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            markers=MarkerStyle(color=mc) if mc is not None else None,
        )


@dataclass
class Heatmap(Chart):
    id: ClassVar[str] = "heatmap"
    nbinsx: int | None = None
    nbinsy: int | None = None
    numbered: bool = True

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Heatmap:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            nbinsx=get_tag_value(f"{chart_id} nbinsx", tags, bool_tags=BOOL_TAGS),
            nbinsy=get_tag_value(f"{chart_id} nbinsy", tags, bool_tags=BOOL_TAGS),
            numbered=get_tag_value(f"{chart_id} numbered", tags, bool_tags=BOOL_TAGS),
        )


@dataclass
class Resid(Chart):
    id: ClassVar[str] = "resid"

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Resid:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
        )


# ── 1D Family ────────────────────────────────────────────────────────────────
# encoding.y, optionally encoding.color (no encoding.x)


@dataclass
class Hist(Chart):
    id: ClassVar[str] = "hist"
    nbins: int | None = None
    border: BorderStyle | None = None
    opacity: float | None = None
    orientation: str | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Hist:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            nbins=get_tag_value(f"{chart_id} nbins", tags, bool_tags=BOOL_TAGS),
            opacity=_get_opacity(tags, chart_id),
            orientation=_get_orientation(tags, chart_id),
        )


@dataclass
class Count(Chart):
    id: ClassVar[str] = "count"

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Count:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
        )


@dataclass
class ECDF(Chart):
    id: ClassVar[str] = "ecdf"
    complementary: bool = False
    markers: bool = False
    lines: bool = True
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> ECDF:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            complementary=get_tag_value(
                f"{chart_id} complementary", tags, bool_tags=BOOL_TAGS
            ),
            markers=get_tag_value(f"{chart_id} markers", tags, bool_tags=BOOL_TAGS),
            lines=get_tag_value(f"{chart_id} lines", tags, bool_tags=BOOL_TAGS),
            opacity=_get_opacity(tags, chart_id),
        )


@dataclass
class Rug(Chart):
    id: ClassVar[str] = "rug"
    height: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Rug:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            height=get_tag_value(f"{chart_id} height", tags, bool_tags=BOOL_TAGS),
        )


# ── Density ──────────────────────────────────────────────────────────────────
# encoding.y required, encoding.x optional (for 2D contour)


@dataclass
class Density(Chart):
    id: ClassVar[str] = "density"
    line_style: LineStyle | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Density:
        color = get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS)
        width = get_tag_value(f"{chart_id} line size", tags, bool_tags=BOOL_TAGS)
        ls = None
        if color is not None or width is not None:
            ls = LineStyle(color=color, width=width)
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            line_style=ls,
            opacity=_get_opacity(tags, chart_id),
        )


# ── Polar Family ─────────────────────────────────────────────────────────────
# encoding.r, encoding.theta, optionally encoding.color


@dataclass
class LinePolar(Chart):
    id: ClassVar[str] = "line_polar"
    line_style: LineStyle | None = None
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> LinePolar:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            line_style=_parse_line_style(tags, chart_id),
            markers=_parse_markers(tags, chart_id),
        )


@dataclass
class ScatterPolar(Chart):
    id: ClassVar[str] = "scatter_polar"
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> ScatterPolar:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            markers=_parse_scatter_markers(tags, chart_id),
        )


@dataclass
class BarPolar(Chart):
    id: ClassVar[str] = "bar_polar"
    border: BorderStyle | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> BarPolar:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            border=_parse_border(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
        )


# ── 3D Family ────────────────────────────────────────────────────────────────
# encoding.x, encoding.y, encoding.z, optionally encoding.color


@dataclass
class Line3D(Chart):
    id: ClassVar[str] = "line_3d"
    line_style: LineStyle | None = None
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Line3D:
        return cls.build(
            encoding=replace(encoding, z=column),
            name=_get_name(tags, chart_id),
            line_style=_parse_line_style(tags, chart_id),
            markers=_parse_markers(tags, chart_id),
        )


@dataclass
class Scatter3D(Chart):
    id: ClassVar[str] = "scatter_3d"
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Scatter3D:
        return cls.build(
            encoding=replace(encoding, z=column),
            name=_get_name(tags, chart_id),
            markers=_parse_scatter_markers(tags, chart_id),
        )


# ── Ternary Family ───────────────────────────────────────────────────────────
# encoding.a, encoding.b, encoding.c, optionally encoding.color


@dataclass
class LineTernary(Chart):
    id: ClassVar[str] = "line_ternary"
    line_style: LineStyle | None = None
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> LineTernary:
        return cls.build(
            encoding=replace(encoding, a=column),
            name=_get_name(tags, chart_id),
            line_style=_parse_line_style(tags, chart_id),
            markers=_parse_markers(tags, chart_id),
        )


@dataclass
class ScatterTernary(Chart):
    id: ClassVar[str] = "scatter_ternary"
    markers: MarkerStyle | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> ScatterTernary:
        return cls.build(
            encoding=replace(encoding, a=column),
            name=_get_name(tags, chart_id),
            markers=_parse_scatter_markers(tags, chart_id),
        )


# ── NamedValues Family ───────────────────────────────────────────────────────
# encoding.names, encoding.values


@dataclass
class Pie(Chart):
    id: ClassVar[str] = "pie"
    sort: bool = False
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Pie:
        return cls.build(
            encoding=replace(encoding, names=encoding.x, values=column, x=None),
            opacity=_get_opacity(tags, chart_id),
        )


@dataclass
class Funnel(Chart):
    id: ClassVar[str] = "funnel"
    border: BorderStyle | None = None
    opacity: float | None = None
    label: Label | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Funnel:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            border=_parse_border(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
            label=_parse_label(tags, chart_id),
        )


@dataclass
class FunnelArea(Chart):
    id: ClassVar[str] = "funnel_area"
    opacity: float | None = None
    text_info: str | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> FunnelArea:
        return cls.build(
            encoding=replace(encoding, names=encoding.x, values=column, x=None),
            opacity=_get_opacity(tags, chart_id),
            text_info=get_tag_value(f"{chart_id} text info", tags, bool_tags=BOOL_TAGS),
        )


# ── Hierarchy Family ─────────────────────────────────────────────────────────
# encoding.names, encoding.values, encoding.parents


@dataclass
class Treemap(Chart):
    id: ClassVar[str] = "treemap"
    maxdepth: int | None = None
    branchvalues: str | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Treemap:
        return cls.build(
            encoding=replace(encoding, values=column),
            maxdepth=get_tag_value(f"{chart_id} maxdepth", tags, bool_tags=BOOL_TAGS),
            branchvalues=get_tag_value(
                f"{chart_id} branchvalues", tags, bool_tags=BOOL_TAGS
            ),
            opacity=_get_opacity(tags, chart_id),
        )


@dataclass
class Sunburst(Chart):
    id: ClassVar[str] = "sunburst"
    maxdepth: int | None = None
    branchvalues: str | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Sunburst:
        return cls.build(
            encoding=replace(encoding, values=column),
            maxdepth=get_tag_value(f"{chart_id} maxdepth", tags, bool_tags=BOOL_TAGS),
            branchvalues=get_tag_value(
                f"{chart_id} branchvalues", tags, bool_tags=BOOL_TAGS
            ),
            opacity=_get_opacity(tags, chart_id),
        )


@dataclass
class Icicle(Chart):
    id: ClassVar[str] = "icicle"
    maxdepth: int | None = None
    branchvalues: str | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Icicle:
        return cls.build(
            encoding=replace(encoding, values=column),
            maxdepth=get_tag_value(f"{chart_id} maxdepth", tags, bool_tags=BOOL_TAGS),
            branchvalues=get_tag_value(
                f"{chart_id} branchvalues", tags, bool_tags=BOOL_TAGS
            ),
            opacity=_get_opacity(tags, chart_id),
        )


# ── Dimensional Family ───────────────────────────────────────────────────────
# encoding.dim, optionally encoding.color


@dataclass
class ScatterMatrix(Chart):
    id: ClassVar[str] = "scatter_matrix"
    diagonal_visible: bool = True

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> ScatterMatrix:
        return cls.build(
            encoding=encoding,
            diagonal_visible=get_tag_value(
                f"{chart_id} diagonal", tags, bool_tags=BOOL_TAGS
            ),
        )


@dataclass
class ParallelCategories(Chart):
    id: ClassVar[str] = "parallel_categories"
    line_color: str | None = None
    line_shape: str | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> ParallelCategories:
        return cls.build(
            encoding=encoding,
            line_color=get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS),
            line_shape=get_tag_value(
                f"{chart_id} line shape", tags, bool_tags=BOOL_TAGS
            ),
        )


@dataclass
class ParallelCoordinates(Chart):
    id: ClassVar[str] = "parallel_coordinates"
    line_color: str | None = None
    line_shape: str | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> ParallelCoordinates:
        return cls.build(
            encoding=encoding,
            line_color=get_tag_value(f"{chart_id} color", tags, bool_tags=BOOL_TAGS),
            line_shape=get_tag_value(
                f"{chart_id} line shape", tags, bool_tags=BOOL_TAGS
            ),
        )


# ── Other ────────────────────────────────────────────────────────────────────


@dataclass
class Timeline(Chart):
    id: ClassVar[str] = "timeline"
    border: BorderStyle | None = None
    opacity: float | None = None

    @classmethod
    def parse(
        cls, tags: list[str], column: str, chart_id: str, encoding: Encoding
    ) -> Timeline:
        return cls.build(
            encoding=replace(encoding, y=column),
            name=_get_name(tags, chart_id),
            border=_parse_border(tags, chart_id),
            opacity=_get_opacity(tags, chart_id),
        )


# ── Shapes ──────────────────────────────────────────────────────────────────


@dataclass
class Text:
    text: str
    x: float | str | None = None
    y: float | str | None = None
    color: str | None = None
    size: float | None = None
    showarrow: bool = True

    @classmethod
    def parse(cls, params: dict) -> Text:
        return cls(
            text=params.get("text", ""),
            x=params.get("x"),
            y=params.get("y"),
            color=params.get("color"),
            size=params.get("size"),
            showarrow=bool(params.get("showarrow", True)),
        )


@dataclass
class XLine:
    loc: float | str
    color: str | None = None
    size: float | None = None
    dash: str | None = None
    alpha: float | None = None
    text: str | None = None

    @classmethod
    def parse(cls, params: dict) -> XLine:
        return cls(
            loc=params["xline"],
            color=params.get("color"),
            size=params.get("size"),
            dash=params.get("dash"),
            alpha=params.get("alpha"),
            text=params.get("text"),
        )


@dataclass
class YLine:
    loc: float | str
    color: str | None = None
    size: float | None = None
    dash: str | None = None
    alpha: float | None = None
    text: str | None = None

    @classmethod
    def parse(cls, params: dict) -> YLine:
        return cls(
            loc=params["yline"],
            color=params.get("color"),
            size=params.get("size"),
            dash=params.get("dash"),
            alpha=params.get("alpha"),
            text=params.get("text"),
        )


@dataclass
class XRect:
    x0: float | str
    x1: float | str
    color: str | None = None
    alpha: float | None = None

    @classmethod
    def parse(cls, params: dict) -> XRect | None:
        vals = params.get("xrect")
        if not isinstance(vals, list) or len(vals) < 2:
            return None
        return cls(
            x0=vals[0],
            x1=vals[1],
            color=params.get("color"),
            alpha=params.get("alpha"),
        )


@dataclass
class YRect:
    y0: float | str
    y1: float | str
    color: str | None = None
    alpha: float | None = None

    @classmethod
    def parse(cls, params: dict) -> YRect | None:
        vals = params.get("yrect")
        if not isinstance(vals, list) or len(vals) < 2:
            return None
        return cls(
            y0=vals[0],
            y1=vals[1],
            color=params.get("color"),
            alpha=params.get("alpha"),
        )


@dataclass
class Rect:
    x0: float | str
    x1: float | str
    y0: float | str
    y1: float | str
    color: str | None = None
    alpha: float | None = None

    @classmethod
    def parse(cls, params: dict) -> Rect | None:
        vals = params.get("rect")
        if not isinstance(vals, list) or len(vals) < 4:
            return None
        return cls(
            x0=vals[0],
            x1=vals[1],
            y0=vals[2],
            y1=vals[3],
            color=params.get("color"),
            alpha=params.get("alpha"),
        )


SHAPE_TYPES = {
    "text": Text,
    "xline": XLine,
    "yline": YLine,
    "xrect": XRect,
    "yrect": YRect,
    "rect": Rect,
}


# ── Top-Level Spec ───────────────────────────────────────────────────────────


@dataclass
class Layout:
    title: str | None = None
    width: float | None = None
    height: float | None = None
    xlabel: str | None = None
    ylabel: str | None = None
    grid: bool | None = None
    xgrid: bool | None = None
    ygrid: bool | None = None
    legend: bool | None = None
    legend_horizontal: bool = False
    x_range: list | None = None
    y_range: list | None = None
    barmode: str | None = None
    noerror: bool = False
    shapes: list = field(default_factory=list)


@dataclass
class ChartSpec:
    traces: list[Chart]
    layout: Layout = field(default_factory=Layout)
