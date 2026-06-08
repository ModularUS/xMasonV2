"""
Plotting functions for xMason simulation results using Plotly.
Produces one interactive HTML plot per output quantity.
"""
import os

import numpy as np
import plotly.graph_objects as go

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Plot configuration registry
# ---------------------------------------------------------------------------

PLOT_CONFIG = {
    "impedance": {
        "ylabel": "|Z| [Ω]",
        "log_y": True,
        "suffix": "impedance",
    },
    "Z-real-imag": {
        "ylabel": "Z [Ω]",
        "log_y": False,
        "suffix": "Z_real_imag",
    },
    "S11": {
        "ylabel": "mag(S₁₁)",
        "log_y": False,
        "suffix": "S11",
    },
    "S11-real-imag": {
        "ylabel": "S₁₁",
        "log_y": False,
        "suffix": "S11_real_imag",
    },
    "S11-phase": {
        "ylabel": "∠S₁₁ [°]",
        "log_y": False,
        "suffix": "S11_phase",
    },
    "return-loss": {
        "ylabel": "Return Loss [dB]",
        "log_y": False,
        "suffix": "return_loss",
    },
    "SWR": {
        "ylabel": "SWR",
        "log_y": False,
        "suffix": "SWR",
    },
}


# ---------------------------------------------------------------------------
# Shared layout
# ---------------------------------------------------------------------------

def _base_layout(ylabel, log_y):
    return go.Layout(
        xaxis=dict(
            title=dict(text="Frequency [Hz]", font=dict(size=18)),
            tickfont=dict(size=15),
            showgrid=True,
            gridcolor="rgba(128,128,128,0.3)",
            gridwidth=0.6,
            minor=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", gridwidth=0.4),
        ),
        yaxis=dict(
            title=dict(text=ylabel, font=dict(size=18)),
            tickfont=dict(size=15),
            type="log" if log_y else "linear",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.3)",
            gridwidth=0.6,
            minor=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", gridwidth=0.4),
        ),
        legend=dict(font=dict(size=12)),
        width=800,
        height=640,
        template="plotly_white",
    )


# ---------------------------------------------------------------------------
# Main plotting function
# ---------------------------------------------------------------------------

def plot_results(sim, result_id="simulation", output_dir=None, output_list=None):
    """
    Plot simulation results. Produces one interactive HTML plot per output quantity.

    :param sim: simulation results dict (keys: "frequency", output keys)
    :param result_id: identifier for filenames
    :param output_dir: directory to save plots
    :param output_list: list of output keys to plot
    """
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "result")
    if output_list is None:
        output_list = ["impedance"]

    freq = sim["frequency"]

    for output_key in output_list:
        cfg = PLOT_CONFIG[output_key]
        layout = _base_layout(cfg["ylabel"], cfg["log_y"])
        fig = go.Figure(layout=layout)

        raw = np.array(sim[output_key])

        if output_key in ("Z-real-imag", "S11-real-imag"):
            label = "Z" if output_key == "Z-real-imag" else "S₁₁"
            fig.add_trace(go.Scatter(
                x=freq, y=raw.real, mode="lines",
                line=dict(color="#D32F2F", width=2),
                name=f"Re({label})", opacity=0.8,
            ))
            fig.add_trace(go.Scatter(
                x=freq, y=raw.imag, mode="lines",
                line=dict(color="#1565C0", width=2),
                name=f"Im({label})", opacity=0.8,
            ))
        elif output_key in ("impedance", "S11"):
            fig.add_trace(go.Scatter(
                x=freq, y=np.abs(raw).tolist(), mode="lines",
                line=dict(color="#D32F2F", width=2),
                name="Model prediction", opacity=0.8,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=freq, y=raw.tolist(), mode="lines",
                line=dict(color="#D32F2F", width=2),
                name="Model prediction", opacity=0.8,
            ))

        path = os.path.join(output_dir, f'{result_id}_{cfg["suffix"]}_plot.html')
        fig.write_html(path, auto_open=True)
        logger.info("Plot saved: %s", path)