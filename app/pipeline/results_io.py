"""
Result saving: CSV export and comparison summary JSON.
"""
import os

import numpy as np
import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


def save_results_csv(results, output_dir, base_name):
    """
    Save simulation results to CSV. Handles complex impedance and all output types.

    :param results: simulation results dict
    :param output_dir: directory to save to
    :param base_name: file name prefix
    """
    csv_data = {"frequency": results["frequency"]}

    if "impedance" in results:
        csv_data["impedance_abs"] = [abs(z) for z in results["impedance"]]
        csv_data["impedance_real"] = [z.real for z in results["impedance"]]
        csv_data["impedance_imag"] = [z.imag for z in results["impedance"]]
    if "S11" in results:
        csv_data["S11_mag"] = [abs(s) for s in results["S11"]]
    if "S11-real-imag" in results:
        csv_data["S11_real"] = [s.real for s in results["S11-real-imag"]]
        csv_data["S11_imag"] = [s.imag for s in results["S11-real-imag"]]
    if "S11-phase" in results:
        csv_data["S11_phase_deg"] = results["S11-phase"]
    if "return-loss" in results:
        csv_data["return_loss_dB"] = results["return-loss"]
    if "SWR" in results:
        csv_data["SWR"] = results["SWR"]

    path = os.path.join(output_dir, f"{base_name}_sim.csv")
    pd.DataFrame(csv_data).to_csv(path, index=False, header=True, sep=',')
    logger.info("Results CSV saved to %s", path)
