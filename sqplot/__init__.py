from .roles import get_col_roles, parse_tag, get_tag_value
from .parser import get_chart_spec


def plot(query: str, **kwargs):
    from .backends.plotly import plot as plotly_plot
    from duckdb import register
    
    for tbl_name, tbl in kwargs.items():
        register(tbl_name, tbl)

    return plotly_plot(query)
