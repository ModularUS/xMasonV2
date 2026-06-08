"""
RF utilities using scikit-rf.

Bridges xMason simulation results to skrf Network objects and provides
Smith chart visualization.
"""
import numpy as np
import matplotlib.pyplot as plt
import skrf as rf

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Bridge: simulation results -> skrf Network
# ---------------------------------------------------------------------------

def simulation_to_network(results, Z_0=50.0):
    """
    Convert xMason simulation results dict to a scikit-rf Network.

    :param results: dict with 'frequency' (Hz) and 'impedance' (complex) lists
    :param Z_0: reference impedance in Ohm
    :return: skrf.Network (1-port)
    """
    freqs_hz = np.array(results["frequency"])
    Z_rf = np.array(results["impedance"])

    # xMason uses e^{-jwt} (physics) convention: Im(Z) > 0 for capacitors.
    # scikit-rf uses e^{+jwt} (engineering): Im(Z) < 0 for capacitors.
    # Conjugate to convert. Only affects phase/Smith chart, not |S11| or RL.
    # Z_rf = Z_rf.conjugate()

    freq = rf.Frequency.from_f(freqs_hz, unit="Hz")

    s11 = (Z_rf - Z_0) / (Z_rf + Z_0)

    s = s11.reshape(-1, 1, 1)

    network = rf.Network(frequency=freq, s=s, z0=Z_0, name="transducer")
    logger.info("Created skrf Network: %d points, %.2e-%.2e Hz, Z_0=%.1f Ohm",
                len(freqs_hz), freqs_hz[0], freqs_hz[-1], Z_0)
    return network


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def _auto_marker_freqs(f_min, f_max, n_markers=6):
    """Generate evenly spaced marker frequencies within the simulation band."""
    step = (f_max - f_min) / (n_markers + 1)
    return [round(f_min + step * (i + 1), 1) for i in range(n_markers)]


def plot_smith(network, output_dir=None, result_id="simulation"):
    """
    Plot Smith chart of a transducer network with frequency markers.

    :param network: skrf.Network (1-port)
    :param output_dir: directory to save the plot (optional)
    :param result_id: identifier for the filename
    """
    fig, ax = plt.subplots(figsize=(7, 7))

    network.plot_s_smith(ax=ax, color="#D32F2F", linewidth=1.5,
                         label="Transducer", draw_labels=True, draw_vswr=True)

    # Add frequency markers (auto-scaled to simulation band)
    freqs_hz = network.frequency.f
    s11_data = network.s[:, 0, 0]
    marker_freqs = _auto_marker_freqs(freqs_hz[0], freqs_hz[-1])

    for mf in marker_freqs:
        idx = np.argmin(np.abs(freqs_hz - mf))
        if idx < len(s11_data):
            s = s11_data[idx]
            ax.plot(s.real, s.imag, 'o', color="#D32F2F", markersize=4)
            ax.annotate(f"{freqs_hz[idx]/1e6:.1f} MHz",
                        xy=(s.real, s.imag), fontsize=7,
                        textcoords="offset points", xytext=(5, 5),
                        color="#D32F2F")

    ax.legend(fontsize=10, loc="lower right")

    z0_val = float(network.z0[0].real)
    ax.set_title(f"Smith Chart (Z0 = {z0_val:.0f} Ohm)", fontsize=13)

    if output_dir:
        path = f"{output_dir}/{result_id}_smith.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        logger.info("Smith chart saved to %s", path)
    plt.show()
