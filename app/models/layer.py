import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


class Layer:
    """
    Stores material properties and geometry for a single layer.
    Precomputes helper variables used in the transfer matrix model.
    Variable names follow the mathematical model in README.md.
    """
    def __init__(self, name: str, thickness: float, polarity: bool, area: float, materials: pd.DataFrame):
        """
        :param name: name of layer material
        :param thickness: thickness of layer in m
        :param polarity: polarization direction, follows convention specified in the mathematical model
        :param area: cross-sectional area in m²
        :param materials: material registry
        """
        self.name = name
        self.A = area
        self.d = thickness

        # Access cells column-wise via .at so each keeps its native dtype.
        # A whole-row .loc[name] slice would upcast every cell to complex128
        # (because c_D/eps_s columns are complex), forcing a lossy float() cast.

        ## Fundamental Properties
        # speed of sound
        self.v = float(materials.at[name, "v"])
        # density
        self.rho = float(materials.at[name, "rho"])

        ## Piezoelectric Properties
        # piezoelectric stiffness constant
        self.polarity = polarity
        h = complex(materials.at[name, "h"])
        self.isPiezo = abs(h) != 0
        self.h = h if self.isPiezo else 0
        if self.isPiezo and not polarity:
            self.h *= -1

        # clamped permittivity ε^S (complex: imaginary part = dielectric loss)
        self.eps_S = complex(materials.at[name, "eps_s"])

        # clamped capacitance
        self.C = ((self.eps_S * self.A) / thickness) if abs(self.eps_S) != 0 else 0  # C_0 = ε^S · A / d

        # mechanical loss enters via tan_m below (in beta and gamma), NOT via a
        # complex c_D — do not reintroduce c_D into gamma or loss is double-counted.
        self.tan_m = float(materials.at[name, "tan_m"])
        self.beta = complex(-self.tan_m * 0.5, 1) * self.A * self.rho * self.v

        piezo_str = "piezo" if self.isPiezo else "mechanical"
        logger.debug("Layer '%s': d=%.3e m, %s, polarity=%s", name, thickness, piezo_str, polarity)

    def gamma(self, angular_freq):
        """
        Complex wave propagation constant. Depends on frequency so cannot be precomputed.
        :param angular_freq: angular frequency in rad/s
        :return: gamma
        """
        return complex(self.tan_m * 0.5, 1) * (angular_freq / self.v)
