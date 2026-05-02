import plotly.io as pio
from ..common import SOOTHING_PASTELS

BACKGROUND_COLOR = '#24242c'
# BACKGROUND_COLOR = '#0d1117'
GRID_COLOR = '#43434f'

def apply_theme():
    custom_template = pio.templates["plotly_dark"]
    custom_template.layout.update(
        {
            "colorway": SOOTHING_PASTELS,
            "paper_bgcolor": BACKGROUND_COLOR,
            "plot_bgcolor": BACKGROUND_COLOR,
            "xaxis": {"gridcolor": GRID_COLOR},
            "yaxis": {"gridcolor": GRID_COLOR},
        }
    )

    pio.templates["custom"] = custom_template
    pio.templates.default = "custom"
    pio.renderers[pio.renderers.default].config = {
        "displayModeBar": False,
        "displaylogo": False,
    }