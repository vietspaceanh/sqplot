from .roles import get_col_roles, parse_tag, get_tag_value
from .parser import get_chart_spec


def plot(query: str):
    from .backends.plotly import plot as plotly_plot

    return plotly_plot(query)
