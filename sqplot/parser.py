from dataclasses import dataclass, field
from typing import Any

from . import specs
from .roles import get_col_roles, get_tag_value, parse_tag


# ─────────────────────────── Chart type resolution ────────────────────────── #

_chart_ids = {cls.id for cls in specs.Chart.__subclasses__()}
_base_tags = {cid.split("_")[0] for cid in _chart_ids}
_compounds = {tuple(cid.split("_")) for cid in _chart_ids if "_" in cid}
_layout_tags = set(specs.Layout.__dataclass_fields__) - {
    "legend_horizontal",
    "x_range",
    "y_range",
    "barmode",
    "shapes",
}


# ──────────────────────── Intermediate representation ─────────────────────── #

@dataclass
class RawTrace:
    chart_id: str
    column: str
    tags: list[str]


@dataclass
class RawSpec:
    encoding: dict[str, str | list[str]] = field(default_factory=dict)
    traces: list[RawTrace] = field(default_factory=list)
    layout_tags: dict[str, Any] = field(default_factory=dict)
    shapes: list = field(default_factory=list)


# ─────────────────────────────── SQL → RawSpec ────────────────────────────── #

def _resolve_chart_type(tags: list[str], trace_tags: list[str]) -> str:
    base_tag = trace_tags[0]
    base_idx = tags.index(base_tag)
    for tag in tags[base_idx + 1 :]:
        if "=" not in tag and (base_tag, tag) in _compounds:
            return f"{base_tag} {tag}"
    return base_tag


def parse_sql(sql: str) -> RawSpec:
    col_roles = get_col_roles(sql)
    raw = RawSpec()
    trace_columns: set[str] = set()

    for column, tags in col_roles.items():
        if column == "__global__":
            for tag_group in tags:
                first_key, _ = parse_tag(tag_group[0])
                if first_key in specs.SHAPE_TYPES:
                    params = dict(parse_tag(t) for t in tag_group)
                    obj = specs.SHAPE_TYPES[first_key].parse(params)
                    if obj is not None:
                        raw.shapes.append(obj)
                else:
                    for t in tag_group:
                        k, v = parse_tag(t)
                        if k in _layout_tags:
                            raw.layout_tags[k] = v if v is not None else True
            continue

        trace_tags = [tag for tag in tags if tag in _base_tags]

        if trace_tags:
            chart_id = _resolve_chart_type(tags, trace_tags)
            raw.traces.append(RawTrace(chart_id=chart_id, column=column, tags=tags))
            trace_columns.add(column)

        for tag in tags:
            key, value = parse_tag(tag)
            if key in specs.Encoding.__dataclass_fields__:
                if key == "dim":
                    raw.encoding.setdefault("dim", []).append(column)
                else:
                    raw.encoding[key] = column
            elif key in _layout_tags and not trace_tags:
                raw.layout_tags[key] = value if value is not None else True

        if "x" in [parse_tag(t)[0] for t in tags]:
            val = get_tag_value("x range", tags, bool_tags=specs.BOOL_TAGS)
            if val is not None:
                raw.layout_tags["x_range"] = val

        if not trace_tags:
            val = get_tag_value("* range", tags, bool_tags=specs.BOOL_TAGS)
            if val is not None:
                raw.layout_tags["y_range"] = val

        if get_tag_value("legend horizontal", tags, bool_tags=specs.BOOL_TAGS):
            raw.layout_tags["legend_horizontal"] = True
        if get_tag_value("bar stacked", tags, bool_tags=specs.BOOL_TAGS):
            raw.layout_tags["barmode"] = "stack"
        if get_tag_value("bar grouped", tags, bool_tags=specs.BOOL_TAGS):
            raw.layout_tags["barmode"] = "group"

    return raw


# ──────────────────────────── RawSpec → ChartSpec ─────────────────────────── #

def _build_encoding(raw_enc: dict[str, str | list[str]]) -> specs.Encoding:
    return specs.Encoding(
        **{k: v for k, v in raw_enc.items() if k in specs.Encoding.__dataclass_fields__}
    )


def _build_layout(layout_tags: dict[str, Any], raw: RawSpec) -> specs.Layout:
    layout = specs.Layout(**{k: v for k, v in layout_tags.items() if v is not None})
    layout.shapes = raw.shapes
    return layout


def build_spec(raw: RawSpec) -> specs.ChartSpec:
    chart_classes = {cls.id: cls for cls in specs.Chart.__subclasses__()}
    encoding = _build_encoding(raw.encoding)
    traces = []
    for raw_trace in raw.traces:
        chart_cls = chart_classes.get(raw_trace.chart_id.replace(" ", "_"))
        if chart_cls is None:
            continue
        trace = chart_cls.parse(
            tags=raw_trace.tags,
            column=raw_trace.column,
            chart_id=raw_trace.chart_id,
            encoding=encoding,
        )
        traces.append(trace)
    layout = _build_layout(raw.layout_tags, raw)
    return specs.ChartSpec(traces=traces, layout=layout)


# ──────────────────────────────── Convenience ─────────────────────────────── #

def get_chart_spec(sql: str) -> specs.ChartSpec:
    return build_spec(parse_sql(sql))
