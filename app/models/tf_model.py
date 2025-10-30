import cmath
import math

import pandas as pd
from sklearn import metrics as met

import numpy as np


def MechanicalLayerMatrix(layer, ang_frequency):
    """
    Calculates 4x4 layer matrix for a purely mechanical layer
    (see README.md, mathematical formulation for details).
    """
    gamma = layer.gamma(ang_frequency)
    ch = cmath.cosh(gamma * layer.d)
    sh = cmath.sinh(gamma * layer.d)
    j = complex(0, 1)
    M = np.zeros((4, 4), dtype=complex)
    M[0, 0] = ch
    M[0, 1] = j * layer.beta * sh
    M[1, 0] = -j * (1 / layer.beta) * sh
    M[1, 1] = ch
    M[2, 2] = complex(1, 0)
    M[3, 3] = complex(1, 0)
    return M


def ParallelMatrix(active_stack, ang_frequency):
    """
    Calculates 4x4 transducer matrix for parallel wiring scheme
    (see README.md, mathematical formulation for details).
    """
    out = np.identity(4, dtype=complex)
    for layer in active_stack:
        if layer.isPiezo:
            gamma = layer.gamma(ang_frequency)
            X = (layer.h ** 2 * layer.C) / (layer.beta * ang_frequency)
            ch = cmath.cosh(gamma * layer.d)
            sh = cmath.sinh(gamma * layer.d)
            P = np.zeros((4, 4), dtype=complex)
            P[0, 0] = (ch - X * sh) / (1 - X * sh)
            P[0, 1] = (sh + 2 * X * (1 - ch)) / (1 - X * sh) * complex(0, layer.beta)
            P[0, 2] = (1 - ch) / (1 - X * sh) * -layer.h * layer.C
            P[1, 0] = sh / ((1 - X * sh) * layer.beta) * complex(0, -1)
            P[1, 1] = (ch - X * sh) / (1 - X * sh)
            P[1, 2] = sh / ((1 - X * sh) * layer.beta) * complex(0, -layer.h * layer.C)
            P[2, 2] = complex(1, 0)
            P[3, 0] = sh / ((2 - X * sh) * layer.beta) * complex(0, -layer.h * layer.C)
            P[3, 1] = (-layer.h * layer.C * (1 - ch)) / (1 - X * sh)
            P[3, 2] = (layer.C * ang_frequency) / (1 - X * sh) * complex(0, -1)
            P[3, 3] = complex(1, 0)
        else:
            P = MechanicalLayerMatrix(layer, ang_frequency)
            x = 0
        out = out.__matmul__(P)

    return out


def SeriesMatrix(active_stack, ang_frequency):
    """
    Calculates 4x4 transducer matrix for series wiring scheme
    (see README.md, mathematical formulation for details).
    """
    out = np.identity(4, dtype=complex)
    for layer in active_stack:
        if layer.isPiezo:
            gamma = layer.gamma(ang_frequency)
            ch = cmath.cosh(gamma * layer.d)
            sh = cmath.sinh(gamma * layer.d)
            S = np.zeros((4, 4), dtype=complex)
            j = complex(0, 1)
            S[0, 0] = ch
            S[0, 1] = j * layer.beta * sh
            S[0, 3] = -j * layer.h * (1 - ch) / ang_frequency
            S[1, 0] = -j * sh / layer.beta
            S[1, 1] = ch
            S[1, 3] = layer.h * sh / (layer.beta * ang_frequency)
            S[2, 0] = layer.h * sh / (layer.beta * ang_frequency)
            S[2, 1] = -j * layer.h * (1 - ch) / ang_frequency
            S[2, 2] = complex(1, 0)
            S[2, 3] = -j / (layer.C * ang_frequency) * (1 - layer.h ** 2 * layer.C * sh / (layer.beta * ang_frequency))
            S[3, 3] = complex(1, 0)
        else:
            S = MechanicalLayerMatrix(layer, ang_frequency)
        out = out.__matmul__(S)

    return out


def ParallelAlternating(active_stack, ang_frequency):
    """
    Calculates 4x4 transducer matrix for parallel alternating wiring scheme
    (see README.md, mathematical formulation for details).
    """
    out = np.identity(4, dtype=complex)
    for layer in active_stack:
        if layer.isPiezo:
            gamma = layer.gamma(ang_frequency)
            X = (layer.h ** 2 * layer.C) / (layer.beta * ang_frequency)
            ch = cmath.cosh(gamma * layer.d)
            sh = cmath.sinh(gamma * layer.d)
            P = np.zeros((4, 4), dtype=complex)
            P[0, 0] = (ch - X * sh) / (1 - X * sh)
            P[0, 1] = (sh + 2 * X * (1 - ch)) / (1 - X * sh) * complex(0, layer.beta)
            P[0, 2] = -(1 - ch) / (1 - X * sh) * -layer.h * layer.C
            P[1, 0] = sh / ((1 - X * sh) * layer.beta) * complex(0, -1)
            P[1, 1] = (ch - X * sh) / (1 - X * sh)
            P[1, 2] = -sh / ((1 - X * sh) * layer.beta) * complex(0, -layer.h * layer.C)
            P[2, 2] = complex(-1, 0)
            P[3, 0] = sh / ((2 - X * sh) * layer.beta) * complex(0, -layer.h * layer.C)
            P[3, 1] = (-layer.h * layer.C * (1 - ch)) / (1 - X * sh)
            P[3, 2] = -(layer.C * ang_frequency) / (1 - X * sh) * complex(0, -1)
            P[3, 3] = complex(-1, 0)
        else:
            P = MechanicalLayerMatrix(layer, ang_frequency)
            x = 0
        out = out.__matmul__(P)

    return out


def TransferFunction(active_stack, ang_frequency, Z_b, mode):
    """
    This function calculates the 2x2 transfer matrix (see README.md, mathematical formulation for details)
    :param active_stack: as explained in `runModel`, a list containing the information about the layers
    :param ang_frequency: angular frequency being tested
    :param Z_b: acoustic impedance of backing material
    :param mode: parallel alternating, parallel or series connection of the piezoelectric layers (see README.md for more
    details)
    :return: 2x2 transfer matrix (see README.md, mathematical formulation for details)
    """
    if mode == "parallel_alt":
        M = ParallelAlternating(active_stack, ang_frequency)
    elif mode == "parallel":
        M = ParallelMatrix(active_stack, ang_frequency)
    elif mode == "series":
        M = SeriesMatrix(active_stack, ang_frequency)
    else:
        raise "Mode not recognized.\nModes are limited to: parallel, series or parallel alternating."

    if mode == "series":
        tf = np.zeros((2, 2), dtype=complex)
        tf[0, 0] = -M[2, 0] + M[2, 3] * ((Z_b * M[1, 0] - M[0, 0]) / (Z_b * M[1, 3] - M[0, 3]))
        tf[0, 1] = M[2, 1] - M[2, 3] * ((Z_b * M[1, 1] - M[0, 1]) / (Z_b * M[1, 3] - M[0, 3]))
        tf[1, 0] = -M[3, 3] * ((Z_b * M[1, 0] - M[0, 0]) / (Z_b * M[1, 3] - M[0, 3]))
        tf[1, 1] = M[3, 3] * ((Z_b * M[1, 1] - M[0, 1]) / (Z_b * M[1, 3] - M[0, 3]))

    else:
        tf = np.zeros((2, 2), dtype=complex)
        tf[0, 0] = -M[2, 2] * ((M[1, 0] * Z_b - M[0, 0]) / (M[1, 2] * Z_b - M[0, 2]))
        tf[0, 1] = M[2, 2] * ((M[1, 1] * Z_b - M[0, 1]) / (M[1, 2] * Z_b - M[0, 2]))
        tf[1, 0] = M[3, 0] - M[3, 2] * ((M[1, 0] * Z_b - M[0, 0]) / (M[1, 2] * Z_b - M[0, 2]))
        tf[1, 1] = -M[3, 1] + M[3, 2] * ((M[1, 1] * Z_b - M[0, 1]) / (M[1, 2] * Z_b - M[0, 2]))

    return tf


def createModel(active_stack, materials, area, mode, backing_load="Air",
                transmission_load="Air"):
    """
    This function uses the same arguments as `runModel` except the frequency band, this is because this
    function only creates a `Transducer` object which contains all the simulation_scripts parameters, but does not run the
    simulation_scripts yet.
    :return: A `Transducer` object.
    """
    active_layers = []

    active_index = 0
    for i in range(0, len(active_stack)):
        polarity = True
        if len(active_stack[i]) == 3:
            polarity = active_stack[i][2]

        # Polarization fix
        l = Layer(active_stack[i][0], active_stack[i][1], polarity, area, materials)
        if l.isPiezo and mode == "parallel_alt":
            if active_index % 2 == 0:
                l.polarity = not l.polarity
                l.h = -l.h
            active_index += 1
        active_layers.append(l)

    Z_b = float(materials.loc[backing_load]["v"]) * float(materials.loc[backing_load]["roh"]) * area
    Z_t = float(materials.loc[transmission_load]["v"]) * float(materials.loc[transmission_load]["roh"]) * area

    return Transducer(active_layers, Z_b, Z_t, mode)


def runModel(active_stack, frequency_band, materials, area, mode, backing_load="Air", transmission_load="Air"):
    """
    This function runs a simulation_scripts of the specified transducer
    :param active_stack: list of layers of the transducer, follows the following format: [layer1, layer2, ...], where
    each layer is itself a list with the following format [material_name, thickness, polarization], the material name
    must be the name of a material found in "material.csv", the thickness is in meters and the polarization is an
    optional boolean that defaults to True, it signifies whether the piezoelectric material has a "different"
    polarization direction. What is meant by different is the following: technically the positive polarization direction
    is from the bottom surface of a layer to the top surface. However, in practice the polarization direction is only
    relevant if the piezoelectric layer do not have the same polarization. If they are all the same then it is not
    relevant. For example let's call polarization from bottom to top "up" and the opposite "down". The following
    configuration "up,down,up" can be specified as follows: "True, False, True" but it is functionally equivalent to
    "False, True, False".
    :param frequency_band: [min, max] frequencies to test in MHz, the step size is hard-coded below at 1 Hz
    :param materials: material registry loaded from materials.csv
    :param area: cross-sectional area of the transducer in mm^2
    :param mode: parallel alternating, parallel or series connection of the piezoelectric layers (see README.md for more
    details)
    :param backing_load: material of the backing of the transducer (defaults to air)
    :param transmission_load: material of the media we are sending the ultrasound waves into (could be human skin for
    example, defaults to air)
    :returns: two objects: a dictionary with keys "frequency" and "impedance", each key leads to a list with all the
    simulated frequencies and obtained impedances. The second object is a `Transducer` object that contains all the
    information of the transducer ready to use for a new simulation_scripts or calculate an impedance at a specific desired
    frequency. (see `Transducer` class for more details)
    """
    area *= 1E-6
    transducer = createModel(active_stack, materials, area, mode, backing_load, transmission_load)

    freq_out = []
    impedance_out = []
    freq_step = 0.001
    f = frequency_band[0]
    while f < frequency_band[1] + freq_step:
        f += freq_step
        Z_E = transducer.calculateImpedance(f)
        freq_out.append(f)
        impedance_out.append(Z_E)

    return {"frequency": freq_out, "impedance": impedance_out}, transducer

class Layer:
    """
    An object that stores all information about a layer: its material properties and geometry, once created it
    precomputes certain helper variables used throughout the model. The variable names are the same used in "README.md"
    in the mathematical model section.
    """
    def __init__(self, name: str, thickness: float, polarity: bool, area: float, materials: pd.DataFrame):
        """
        :param name: name of layer material
        :param thickness: thickness of layer in m
        :param polarity: polarization direction, follows convention specified in the mathematical model
        :param area: cross-sectional area in mm^2
        :param materials: material registry
        """
        self.name = name
        self.A = area
        self.d = thickness

        material = materials.loc[name]

        self.polarity = polarity
        # elastic stiffness constant
        self.c = complex(material["c33"])
        if self.c.__abs__() == 0:
            self.c_d = 0
            self.c_tan = 0
        else:
            self.c_d = self.c.real
            self.c_tan = self.c.imag / self.c_d
            # Uncomment to deactivate mechanical losses
            # self.c_tan = 0

        # speed of sound
        self.v = complex(material["v"])
        # density
        self.rho = float(material["roh"])

        h33 = complex(material["h33"])
        self.isPiezo = h33.__abs__() != 0

        # electric permeability
        self.epsilon = complex(material["eps33"])
        if self.epsilon.__abs__() == 0:
            self.epsilon_s = 0
            self.epsilon_tan = 0
            self.C = 0
        else:
            self.epsilon_s = self.epsilon.real
            self.epsilon_tan = -(self.epsilon.imag / self.epsilon_s)
            # Uncomment to deactivate mechanical losses
            # self.epsilon_tan = 0
            self.C = (self.epsilon / thickness) * self.A

        if h33.__abs__() == 0:
            # material is not piezoelectric
            self.e = 0
            self.h = 0
        else:
            # piezoelectric constant
            self.e = h33 * self.epsilon
            # transmission constant
            self.h = h33
            if not polarity:
                self.h *= -1

        # complex acoustic impedance
        self.beta = complex(-self.c_tan * 0.5, 1) * self.A * self.rho * self.v

    def gamma(self, frequency):
        """
        One of the helper variables used in the model. Gamma, the complex wave propagation constant. It cannot be
        precomputed as it depends on the frequency. This method calculates it.
        :param frequency: angular frequency in rad/s
        :return: gamma
        """
        return complex(self.c_tan * 0.5, 1) * (frequency / self.v)

class Transducer:
    """
    An object that represents a transducer, it stores its layers and backing/transmission impedances
    it is an output of the `runModel` function.
    """
    def __init__(self, layers: list[Layer], Z_b: float, Z_t: float, mode: str):
        """
        :param layers: list containing the layers of the transducer
        :param Z_b: acoustic impedance of backing medium (see README.md algorithm section)
        :param Z_t: acoustic impedance of transmission medium (see README.md algorithm section)
        :param mode: a string that specifies the wiring scheme. The options are: parallel, parallel_alt and series
        (see README.md algorithm section)
        """
        self.layers = layers
        self.Z_b = Z_b
        self.Z_t = Z_t
        self.mode = mode

    def calculateImpedance(self, frequency):
        """
        Calculates the total impedance of the transducer at the given frequency.
        (see README.md mathematical model section for explanation of the formula)
        :param frequency: frequency in MHz
        :return: absolute impedance in ohm
        """
        tf = TransferFunction(self.layers, 2 * math.pi * frequency * 1E6, self.Z_b, self.mode)
        Z_E = (tf[0, 0] * self.Z_t + tf[0, 1]) / (tf[1, 0] * self.Z_t + tf[1, 1])
        #return Z_E.__abs__()
        return Z_E

    def calculateR2Score(self, experimental_x, experimental_y):
        """
        Calculates R2 score of the model
        :param experimental_x: x values of experimental datapoints
        :param experimental_y: y values of experimental datapoints
        :return: R2 score
        """
        experimental_x = experimental_x.to_list()
        experimental_y = experimental_y.to_list()
        predicted_y = []
        for i in range(len(experimental_x)):
            f = experimental_x[i]
            predicted_y.append(self.calculateImpedance(f))
        return met.r2_score(experimental_y, predicted_y)
