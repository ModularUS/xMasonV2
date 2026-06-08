"""
Transducer model: TransferFunction and Transducer class.
Pure model logic — no orchestration or I/O.
"""
import math

import numpy as np
import pandas as pd
from sklearn import metrics as met

from app.models.layer import Layer
from app.models.matrices import ParallelAlternating, ParallelMatrix, SeriesMatrix
from app.utils.logger import get_logger

logger = get_logger(__name__)


def TransferFunction(active_stack, ang_frequency, Z_b, mode):
    """
    Calculates the 2x2 transfer matrix by reducing the 4x4 system matrix
    using the backing impedance boundary condition.
    :param active_stack: list of Layer objects
    :param ang_frequency: angular frequency in rad/s
    :param Z_b: acoustic impedance of backing material
    :param mode: parallel_alt, parallel or series
    :return: 2x2 transfer matrix
    """
    if mode == "parallel_alt":
        M = ParallelAlternating(active_stack, ang_frequency)
    elif mode == "parallel":
        M = ParallelMatrix(active_stack, ang_frequency)
    elif mode == "series":
        M = SeriesMatrix(active_stack, ang_frequency)
    else:
        logger.error("Unrecognized mode: '%s'", mode)
        raise ValueError("Mode not recognized.\nModes are limited to: parallel, series or parallel_alt.")

    if mode == "series":
        denom = Z_b * M[1, 3] + M[0, 3]

        A = -M[2, 0] + M[2, 3] * (Z_b * M[1, 0] + M[0, 0]) / denom
        B =  M[2, 1] - M[2, 3] * (Z_b * M[1, 1] + M[0, 1]) / denom
        C = -M[3, 3] *            (Z_b * M[1, 0] + M[0, 0]) / denom
        D =  M[3, 3] *            (Z_b * M[1, 1] + M[0, 1]) / denom
    else:
        denom = M[1, 2] * Z_b - M[0, 2]
        A = -M[2, 2] * (M[1, 0] * Z_b - M[0, 0]) / denom
        B =  M[2, 2] * (M[1, 1] * Z_b - M[0, 1]) / denom
        C =  M[3, 0] - M[3, 2] * (M[1, 0] * Z_b - M[0, 0]) / denom
        D = -M[3, 1] + M[3, 2] * (M[1, 1] * Z_b - M[0, 1]) / denom

    return A, B, C, D


def create_transducer(active_stack, materials, area, mode, backing_load="Air",
                      transmission_load="Air", Z_0=50.0):
    """
    Creates a Transducer object from a stack definition.
    :param active_stack: list of layers [[material_name, thickness, polarization], ...]
    :param materials: material registry (DataFrame)
    :param area: cross-sectional area in m^2
    :param mode: parallel_alt, parallel or series
    :param backing_load: backing material name (defaults to Air)
    :param transmission_load: transmission material name (defaults to Air)
    :param Z_0: electrical reference impedance in Ohm (default 50.0, standard VNA)
    :return: A Transducer object.
    """
    logger.info("Creating transducer model: %d layers, mode='%s', backing='%s', transmission='%s', Z_0=%.1f Ohm",
                len(active_stack), mode, backing_load, transmission_load, Z_0)
    active_layers = []

    for name, thickness, polarity in active_stack:
        active_layers.append(Layer(name, thickness, polarity, area, materials))

    Z_b = float(materials.at[backing_load, "v"]) * float(materials.at[backing_load, "rho"]) * area
    Z_t = float(materials.at[transmission_load, "v"]) * float(materials.at[transmission_load, "rho"]) * area
    logger.debug("Boundary impedances: Z_b=%.4e, Z_t=%.4e", Z_b, Z_t)
    return Transducer(active_layers, Z_b, Z_t, mode, Z_0)


class Transducer:
    """
    Represents a transducer with its layers and boundary conditions.
    Can calculate impedance and derived RF quantities at any frequency.
    """
    def __init__(self, layers: list[Layer], Z_b: float, Z_t: float, mode: str, Z_0: float = 50.0):
        self.layers = layers
        self.Z_b = Z_b  # acoustic impedance backing layer
        self.Z_t = Z_t  # acoustic impedance transmission medium
        self.Z_0 = Z_0  # electrical reference impedance (Ohm)
        self.mode = mode

    def calculateImpedance(self, frequency):
        """
        Calculates the total electrical impedance at the given frequency.
        :param frequency: frequency in Hz
        :return: complex impedance
        """
        A, B, C, D = TransferFunction(self.layers, 2 * math.pi * frequency, self.Z_b, self.mode)
        return (A * self.Z_t + B) / (C * self.Z_t + D)  # Eq. 3.61

    def calculateS11(self, frequency):
        """
        Calculates the S11 reflection coefficient at the given frequency.
        :param frequency: frequency in Hz
        :return: complex S11
        """
        Z_E = self.calculateImpedance(frequency)
        return (Z_E - self.Z_0) / (Z_E + self.Z_0)

    def calculateS11phase(self, frequency):
        """
        Calculates the S11 phase at the given frequency.
        :param frequency: frequency in Hz
        :return: S11 phase
        """
        S11 = self.calculateS11(frequency)
        return np.degrees(np.angle(S11))

    def calculateRL(self, frequency):
        """
        Calculates the return loss at the given frequency.
        :param frequency: frequency in Hz
        :return: return loss in dB (negative value, closer to 0 = worse match)
        """
        S11 = self.calculateS11(frequency)
        return 20 * np.log10(abs(S11))

    def calculateSWR(self, frequency):
        """
        Calculates the standing wave ratio at the given frequency.
        :param frequency: frequency in Hz
        :return: SWR (1.0 = perfect match, inf = total reflection)
        """
        S11 = self.calculateS11(frequency)
        return (1 + abs(S11)) / (1 - abs(S11))

    def calculateR2Score(self, experimental_x, experimental_y):
        """
        Calculates R2 score of the model against experimental data.
        """
        experimental_x = experimental_x.to_list()
        experimental_y = experimental_y.to_list()
        predicted_y = []
        for i in range(len(experimental_x)):
            predicted_y.append(self.calculateImpedance(experimental_x[i]))
        return met.r2_score(experimental_y, predicted_y)
