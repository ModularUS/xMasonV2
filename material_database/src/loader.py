"""
Loader API for the material database.

Reads compiled materials (from build/materials.json) and returns them
in the same pandas DataFrame format that the simulation code expects.

Usage:
    from material_database.loader import load_materials, get_material

    materials = load_materials()          # full DataFrame
    pvdf = get_material("P(VDF-TrFE)")   # single material as dict
"""

import os
import json
import pandas as pd

BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build")
JSON_PATH = os.path.join(BUILD_DIR, "materials.json")


def _load_json():
    if not os.path.exists(JSON_PATH):
        raise FileNotFoundError(
            f"Compiled materials not found at {JSON_PATH}. "
            "Run 'python scripts/compile.py' first."
        )
    with open(JSON_PATH, "r") as f:
        return json.load(f)


def load_materials() -> pd.DataFrame:
    """
    Load all materials as a pandas DataFrame.

    - Index: material names
    - Columns: rho, v, c_D, tan_m, eps_r_T, tan_e, eps_s, h, d
    - Complex properties stored as Python complex objects
    """
    data = _load_json()

    rows = {}
    for name, props in data.items():
        c_D = props.get("c_D", 0)
        if isinstance(c_D, dict):
            c_D = complex(c_D["real"], c_D["imag"])

        eps_s = props.get("eps_s", 0)
        if isinstance(eps_s, dict):
            eps_s = complex(eps_s["real"], eps_s["imag"])

        rows[name] = {
            "rho": props["rho"],
            "v": props.get("v", 0),
            "c_D": c_D,
            "tan_m": props.get("tan_m", 0),
            "eps_r_T": props.get("eps_r_T", 0),
            "tan_e": props.get("tan_e", 0),
            "eps_s": eps_s,
            "h": props.get("h", 0),
            "d": props.get("d", 0),
        }

    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "Material"
    return df


def get_material(name: str) -> dict:
    """
    Get a single material's properties as a dict.

    Raises KeyError if the material is not found.
    """
    data = _load_json()
    if name not in data:
        raise KeyError(f"Material '{name}' not found. Available: {list(data.keys())}")

    props = data[name]
    for key in ("c_D", "eps_s"):
        val = props.get(key, 0)
        if isinstance(val, dict):
            props[key] = complex(val["real"], val["imag"])
    return props


def list_materials() -> list[str]:
    """Return a list of all available material names."""
    return list(_load_json().keys())
