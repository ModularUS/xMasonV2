"""
YAML-driven simulation runner.
Thin orchestrator: parse config -> run simulation -> save -> plot.
"""
import os
import shutil
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "material_database", "src"))

from material_database.src.loader import load_materials
from app.pipeline.simulation import runModel
from app.pipeline.config_parser import parse_yaml_config
from app.pipeline.results_io import save_results_csv
from app.pipeline.plotting import plot_results
from app.analysis.rf_utils import simulation_to_network, plot_smith
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_simulation(config):
    """
    Run the transducer simulation from a parsed config.

    :param config: SimConfig object
    :return: (results dict, Transducer model)
    """
    return runModel(
        active_stack=config.stack,
        frequency_band=config.freq_band,
        materials=materials,
        area=config.area,
        mode=config.connection,
        transmission_load=config.transmission_material,
        backing_load=config.backing_material,
        Z_0=config.source_impedance,
        outputs=config.output_list,
        freq_step=config.freq_step,
    )


def run_yaml_config(yaml_config, materials, output_dir):
    """
    Full pipeline for a single YAML config: parse -> simulate -> save -> plot.

    :param yaml_config: config filename (e.g. 'pvdfstack.yaml')
    :param materials: loaded material registry
    :param output_dir: directory for all outputs
    :return: (results, config) or (None, None) on failure
    """
    configs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    yaml_path = os.path.join(configs_dir, yaml_config)

    config = parse_yaml_config(yaml_path, materials)
    if config is None:
        return None, None

    # --- Simulate ---
    results, model = runModel(
        active_stack=config.stack,
        frequency_band=config.freq_band,
        materials=materials,
        area=config.area,
        mode=config.connection,
        transmission_load=config.transmission_material,
        backing_load=config.backing_material,
        Z_0=config.source_impedance,
        outputs=config.output_list,
        freq_step=config.freq_step,
    )

    # --- Save CSV ---
    save_results_csv(results, output_dir, config.base_name)

    # --- Copy config for reproducibility ---
    shutil.copy2(config.config_path, output_dir)

    logger.info("Processing: %s", config.base_name)
    logger.info("Output dir: %s", output_dir)

    # --- Plot simulation results ---
    plot_results(results, result_id=config.base_name,
                 output_dir=output_dir, output_list=config.output_list)

    # --- Smith chart ---
    if "impedance" in config.output_list:
        network = simulation_to_network(results, Z_0=config.source_impedance)
        plot_smith(network, output_dir=output_dir, result_id=config.base_name)

    return results, config


if __name__ == "__main__":
    SCRATCH_DIR = os.path.join(PROJECT_ROOT, "scratch")
    materials = load_materials()

    configs_to_run = ['pvdfstack.yaml']

    for yaml_config in configs_to_run:
        config_base = os.path.basename(yaml_config).rsplit('.', 1)[0]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(SCRATCH_DIR, f"{config_base}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)

        results, config = run_yaml_config(yaml_config, materials, output_dir)

        if results is None:
            logger.error("Simulation failed for %s", yaml_config)