"""
Pydantic models defining the schema for material properties.

These models serve two purposes:
1. Validate material YAML files at compile time (catch typos, wrong types, missing required fields)
2. Document what properties exist, their units, and which are optional
"""

from typing import Optional, Literal
from pydantic import BaseModel, model_validator


class ComplexProperty(BaseModel):
    """Property that can have a loss/imaginary component (e.g. stiffness, permittivity)."""
    real: float
    imag: float = 0.0
    unit: str = ""
    name: str = ""


class ScalarProperty(BaseModel):
    """Simple float property with a unit."""
    value: float
    unit: str = ""
    name: str = ""


class Source(BaseModel):
    """Reference for where a property value came from."""
    property: list[str]
    reference: str
    note: str = ""


class MaterialProperties(BaseModel):
    """
    All possible material properties.

    Only rho (density) is required. Everything else is optional because:
    - Non-piezoelectric materials don't have c_D, h, d, eps_r_T, etc.
    - Some properties can be derived from others (v from c_D/rho, h from d, etc.)
    """

    # Fundamental — required for all materials
    rho: ScalarProperty                              # density [kg/m^3]
    v: Optional[ScalarProperty] = None               # speed of sound [m/s]

    # Piezoelectric model — stiffness (provide c_D or c_E, one is sufficient)
    c_D: Optional[ComplexProperty] = None            # open-circuit elastic stiffness [N/m^2]
    c_E: Optional[ComplexProperty] = None            # short-circuit elastic stiffness [N/m^2]
    tan_m: Optional[ScalarProperty] = None           # mechanical loss tangent [-]
    Q_m: Optional[ScalarProperty] = None             # mechanical quality factor [-] (alternative to tan_m)

    # Piezoelectric model — permittivity (provide eps_r_T or eps_r_S, one is sufficient)
    eps_r_T: Optional[ScalarProperty] = None         # relative permittivity, free/unclamped [-]
    eps_r_S: Optional[ScalarProperty] = None         # relative permittivity, clamped [-]
    tan_e: Optional[ScalarProperty] = None           # dielectric loss tangent [-]
    Q_e: Optional[ScalarProperty] = None             # dielectric quality factor [-] (alternative to tan_e)

    # Piezoelectric model — coupling (at least one of d, e, h for piezo materials)
    d: Optional[ScalarProperty] = None               # piezoelectric charge constant [C/N]
    e: Optional[ScalarProperty] = None               # piezoelectric stress constant [C/m^2]
    h: Optional[ScalarProperty] = None               # piezoelectric stiffness constant [V/m]
    g: Optional[ScalarProperty] = None               # piezoelectric voltage constant [Vm/N]
    k_t: Optional[ScalarProperty] = None             # thickness coupling factor [-]

    @model_validator(mode="after")
    def check_derivability(self):
        """Speed of sound must be determinable (need either v, c_D, or c_E + rho)."""
        if self.v is None and self.c_D is None and self.c_E is None:
            raise ValueError(
                "Must provide either 'v' (speed of sound), 'c_D' (open-circuit stiffness), "
                "or 'c_E' (short-circuit stiffness) so speed of sound can be derived"
            )
        return self

    @model_validator(mode="after")
    def check_tan_m_or_Q_m(self):
        """Only one of tan_m or Q_m may be specified."""
        if self.tan_m is not None and self.Q_m is not None:
            raise ValueError(
                "Specify either 'tan_m' or 'Q_m', not both."
            )
        return self

    @model_validator(mode="after")
    def check_tan_e_or_Q_e(self):
        """Only one of tan_e or Q_e may be specified."""
        if self.tan_e is not None and self.Q_e is not None:
            raise ValueError(
                "Specify either 'tan_e' or 'Q_e', not both."
            )
        return self


class Vendor(BaseModel):
    """Material vendor/supplier information."""
    name: str = ""
    url: str = ""


class Material(BaseModel):
    """Top-level model representing a single material."""

    name: str
    category: Literal["piezoelectric", "metal", "polymer", "fluid", "composite"]
    vendor: Optional[Vendor] = None
    properties: MaterialProperties
    sources: list[Source] = []
