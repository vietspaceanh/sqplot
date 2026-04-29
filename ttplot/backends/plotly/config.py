import plotly.io as pio
from ..common import SOOTHING_PASTELS

def apply_theme():
    custom_template = pio.templates["plotly_dark"]
    custom_template.layout.update(
        {
            "colorway": SOOTHING_PASTELS,
            "paper_bgcolor": "#24242c",
            "plot_bgcolor": "#24242c",
            "xaxis": {"gridcolor": "#43434f"},
            "yaxis": {"gridcolor": "#43434f"},
        }
    )

    pio.templates["custom"] = custom_template
    pio.templates.default = "custom"
    pio.renderers[pio.renderers.default].config = {
        "displayModeBar": False,
        "displaylogo": False,
    }