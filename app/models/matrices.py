"""
Pure matrix computation functions for the transfer matrix model.
Each function takes layer(s) and angular frequency, returns a numpy matrix.
"""
import cmath

import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


def MechanicalLayerMatrix(layer, ang_frequency):
    """
    Calculates 4x4 layer matrix for a purely mechanical layer.
    """
    j = complex(0, 1)
    B = layer.beta
    ch = cmath.cosh(layer.gamma(ang_frequency) * layer.d)
    sh = cmath.sinh(layer.gamma(ang_frequency) * layer.d)

    return np.array([
        [ch,           j*B*sh,     0,   0], #sign error Almohimeed
        [-j*sh/B,      ch,         0,   0], #sign error Almohimeed
        [0,            0,          1,   0],
        [0,            0,          0,   1],
    ], dtype=complex)


def SeriesMatrix(active_stack, ang_frequency):
    """
    Calculates 4x4 transducer matrix for series wiring scheme.
    """
    out = np.identity(4, dtype=complex)
    j = complex(0, 1)

    for layer in active_stack:
        if layer.isPiezo:
            w = ang_frequency
            h, C, B = layer.h, layer.C, layer.beta
            ch = cmath.cosh(layer.gamma(w) * layer.d)
            sh = cmath.sinh(layer.gamma(w) * layer.d)

            S = np.array([
                [ch,            j*B*sh,         0,   -j*h*(1 - ch)/w                              ],
                [-j*sh/B,       ch,             0,    h*sh/(B*w)                                   ],
                [h*sh/(B*w),   -j*h*(1 - ch)/w, 1,   -j/(C*w) * (1 - h**2*C*sh/(B*w))            ],
                [0,             0,              0,    1                                             ],
            ], dtype=complex)
        else:
            S = MechanicalLayerMatrix(layer, ang_frequency)
        out = out @ S

    return out


def ParallelMatrix(active_stack, ang_frequency):
    """
    Calculates 4x4 transducer matrix for parallel wiring scheme.
    """
    out = np.identity(4, dtype=complex)
    j = complex(0, 1)

    for layer in active_stack:
        if layer.isPiezo:
            w = ang_frequency
            h, C, B = layer.h, layer.C, layer.beta
            X = (h**2 * C) / (B * w)
            ch = cmath.cosh(layer.gamma(w) * layer.d)
            sh = cmath.sinh(layer.gamma(w) * layer.d)
            D = 1 - X * sh

            P = np.array([
                [(ch - X*sh)/D,              j*B*(sh + 2*X*(1 - ch))/D,   h*C*(1 - ch)/D,            0],
                [-j*sh/(B*D),                (ch - X*sh)/D,               j*h*C*sh/(B*D),            0],
                [0,                          0,                           1,                         0],
                [-j*h*C*sh/(B*(2 - X*sh)),   -h*C*(1 - ch)/D,             j*C*w/D,                   1],
            ], dtype=complex)
        else:
            P = MechanicalLayerMatrix(layer, ang_frequency)
        out = out @ P

    return out


def ParallelAlternating(active_stack, ang_frequency):
    """
    Calculates 4x4 transducer matrix for parallel alternating wiring scheme.
    Based on P̄ᴹ (Almohimeed 2020, Eq. 3.40) with column 2 coupling terms
    sign-absorbed for the +V state vector convention used by TransferFunction.
    """
    out = np.identity(4, dtype=complex)
    j = complex(0, 1)

    for layer in active_stack:
        if layer.isPiezo:
            w = ang_frequency
            h, C, B = layer.h, layer.C, layer.beta
            X = (h**2 * C) / (B * w)
            ch = cmath.cosh(layer.gamma(w) * layer.d)
            sh = cmath.sinh(layer.gamma(w) * layer.d)
            D = 1 - X * sh

            P = np.array([
                [(ch - X*sh)/D,    j*B*(sh + 2*X*(1 - ch))/D,     -h*C*(1 - ch)/D,           0],
                [-j*sh/(B*D),      (ch - X*sh)/D,                 -j*h*C*sh/(B*D),           0],
                [0,                0,                             -1,                         0],
                [-j*h*C*sh/(B*(2 - X*sh)),  -h*C*(1 - ch)/D,      -j*C*w/D,                 -1],
            ], dtype=complex)
        else:
            P = MechanicalLayerMatrix(layer, ang_frequency)
        out = out @ P

    return out
