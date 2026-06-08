"""
Simulation orchestration: frequency sweep execution.
Bridges configuration/materials to the Transducer model.
"""
from app.models.transducer import create_transducer
from app.utils.logger import get_logger

logger = get_logger(__name__)


VALID_OUTPUTS = {"impedance", "Z-real-imag", "S11", "S11-real-imag", "S11-phase", "return-loss", "SWR"}


def runModel(active_stack, frequency_band, materials, area, mode, backing_load="Air",
             transmission_load="Air", Z_0=50.0, outputs=None, freq_step=1000):
    """
    Runs a simulation of the specified transducer across a frequency band.
    :param active_stack: list of layers [[material_name, thickness, polarization], ...]
    :param frequency_band: [min, max] frequencies in Hz
    :param materials: material registry (DataFrame)
    :param area: cross-sectional area in m²
    :param mode: parallel_alt, parallel or series
    :param backing_load: backing material (defaults to Air)
    :param transmission_load: transmission material (defaults to Air)
    :param Z_0: electrical reference impedance in Ohm (default 50.0)
    :param outputs: list of quantities to compute (default ["impedance"])
                    available: impedance, S11, S11-real-imag, S11-phase, return-loss, SWR
    :returns: (dict with "frequency" and requested output lists, Transducer object)
    """
    if outputs is None:
        outputs = ["impedance"]

    transducer = create_transducer(active_stack, materials, area, mode,
                                   backing_load, transmission_load, Z_0)

    logger.info("Running simulation: %.2e - %.2e Hz, mode='%s', outputs=%s",
                frequency_band[0], frequency_band[1], mode, outputs)

    freq_out = []
    results = {key: [] for key in outputs}
    results["frequency"] = freq_out

    s11_keys = {"S11", "S11-real-imag", "S11-phase", "return-loss", "SWR"}
    compute_s11 = bool(s11_keys & set(outputs))

    f = frequency_band[0]
    while f < frequency_band[1] + freq_step:
        f += freq_step
        Z_E = transducer.calculateImpedance(f)
        freq_out.append(f)

        if "impedance" in outputs:
            results["impedance"].append(Z_E)
        if "Z-real-imag" in outputs:
            results["Z-real-imag"].append(Z_E)

        if compute_s11:
            if "S11" in outputs:
                results["S11"].append(transducer.calculateS11(f))
            if "S11-real-imag" in outputs:
                results["S11-real-imag"].append(transducer.calculateS11(f))
            if "S11-phase" in outputs:
                results["S11-phase"].append(transducer.calculateS11phase(f))
            if "return-loss" in outputs:
                results["return-loss"].append(transducer.calculateRL(f))
            if "SWR" in outputs:
                results["SWR"].append(transducer.calculateSWR(f))

    logger.info("Simulation complete: %d frequency points computed", len(freq_out))
    return results, transducer