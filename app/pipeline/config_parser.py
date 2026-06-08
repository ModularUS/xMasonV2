"""
YAML configuration parser and validator for xMason simulations.
"""
import math
import os
from dataclasses import dataclass, field

import yaml

from app.pipeline.simulation import VALID_OUTPUTS
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SimConfig:
    """Parsed and validated simulation configuration."""
    area: float                          # m²
    connection: str                      # parallel_alt, parallel, series
    backing_material: str                # material name
    transmission_material: str           # material name
    freq_band: list                      # [min, max] Hz
    freq_step: float                     # Hz
    source_impedance: float              # Ohm
    output_list: list                    # output types to compute
    stack: list                          # [[material, thickness, polarity], ...]
    config_path: str = ""                # resolved path to YAML file
    base_name: str = ""                  # config name without extension


def parse_yaml_config(yaml_path, materials):
    """
    Parse and validate a single YAML config file.

    :param yaml_path: path to the YAML file
    :param materials: loaded material registry (DataFrame)
    :return: SimConfig or None if validation fails
    """
    name = os.path.basename(yaml_path)

    with open(yaml_path, "r") as stream:
        try:
            f = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.error("YAML parse error in %s: %s", name, exc)
            return None

    # --- Area ---
    diameter = f.get("diameter")
    side_length = f.get("side_length")
    area = f.get("area")

    if diameter is None and side_length is None and area is None:
        logger.warning("No area specified. Skipping %s.", name)
        return None

    if diameter is not None and diameter <= 0:
        logger.warning("Diameter must be positive. Skipping %s.", name)
        return None
    if side_length is not None and side_length <= 0:
        logger.warning("Side length must be positive. Skipping %s.", name)
        return None
    if area is not None and area <= 0:
        logger.warning("Area must be positive. Skipping %s.", name)
        return None

    if diameter is not None:
        area = (diameter / 2) ** 2 * math.pi
    elif side_length is not None:
        area = side_length ** 2

    # --- Connection ---
    connection = f.get("connection")
    valid_connections = {"parallel-alternating", "parallel", "series"}
    if connection not in valid_connections:
        logger.warning("Invalid or missing connection type '%s'. Skipping %s.", connection, name)
        return None
    if connection == "parallel-alternating":
        connection = "parallel_alt"

    # --- Materials ---
    backing_material = f.get("backing-material", "Air")
    if backing_material not in materials.index:
        logger.warning("Backing material '%s' not found. Skipping %s.", backing_material, name)
        return None

    transmission_material = f.get("transmission-material", "Air")
    if transmission_material not in materials.index:
        logger.warning("Transmission material '%s' not found. Skipping %s.", transmission_material, name)
        return None

    # --- Frequency band ---
    freq_config = f.get("frequency-band")
    if freq_config is None:
        logger.warning("No frequency band specified. Skipping %s.", name)
        return None

    min_freq = freq_config.get("min")
    max_freq = freq_config.get("max")
    if min_freq is None or max_freq is None:
        logger.warning("Frequency band min/max missing. Skipping %s.", name)
        return None
    if min_freq <= 0 or max_freq <= 0 or min_freq >= max_freq:
        logger.warning("Invalid frequency band [%s, %s]. Skipping %s.", min_freq, max_freq, name)
        return None

    freq_step = freq_config.get("step", 1000)
    if freq_step <= 0:
        logger.warning("Frequency step must be positive. Skipping %s.", name)
        return None

    # --- Source impedance ---
    source_impedance = f.get("source-impedance", 50.0)
    if source_impedance <= 0:
        logger.warning("Source impedance must be positive. Skipping %s.", name)
        return None

    # --- Outputs ---
    output_list = f.get("output", ["impedance"])

    invalid_outputs = [o for o in output_list if o not in VALID_OUTPUTS]
    if invalid_outputs:
        logger.warning("Invalid output types %s. Skipping %s.", invalid_outputs, name)
        return None

    # --- Transducer stack ---
    stack = []
    for index, layer in enumerate(f.get("transducer", [])):
        material = layer.get("material")
        if material is None:
            logger.warning("No material for layer %d. Skipping %s.", index, name)
            return None
        if material not in materials.index:
            logger.warning("Material '%s' in layer %d not found. Skipping %s.", material, index, name)
            return None

        thickness = layer.get("thickness")
        if thickness is None or thickness <= 0:
            logger.warning("Invalid thickness for layer %d. Skipping %s.", index, name)
            return None
        # thickness expected in meters (SI)

        pol_str = layer.get("polarization", "up")
        polarity = pol_str == "up"  # up=+h, down=-h

        stack.append([material, thickness, polarity])

    if len(stack) == 0:
        logger.warning("No layers specified. Skipping %s.", name)
        return None

    base_name = name.rsplit(".", 1)[0]

    logger.info("Parsed config '%s': %d layers, %s, %.2e-%.2e Hz",
                name, len(stack), connection, min_freq, max_freq)

    return SimConfig(
        area=area,
        connection=connection,
        backing_material=backing_material,
        transmission_material=transmission_material,
        freq_band=[min_freq, max_freq],
        freq_step=freq_step,
        source_impedance=source_impedance,
        output_list=output_list,
        stack=stack,
        config_path=yaml_path,
        base_name=base_name,
    )
