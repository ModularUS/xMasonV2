"""
Compile material YAML files into machine-readable formats.

Usage:
    python scripts/compile.py

Reads all YAML files from materials/, validates them, derives missing
properties, and outputs:
    - build/materials.json  (machine format)
    - build/materials.csv   (reference format)
"""

import sys
import os
import json
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
MATERIALS_DIR = os.path.join(REPO_ROOT, "materials")
BUILD_DIR = os.path.join(REPO_ROOT, "build")

sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
from models import Material

# Vacuum permittivity [F/m]
eps_0 = 8.85418782e-12


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_prop_value(props, key):
    """Get a scalar property value, or None if not set."""
    p = getattr(props, key, None)
    return p.value if p is not None else None


def get_complex_prop(props, key):
    """Get a complex property as a complex number, or None if not set."""
    p = getattr(props, key, None)
    if p is None:
        return None
    return complex(p.real, p.imag)


def validate_material(material):
    """
    Check that enough properties are given to fully define this material.
    Returns list of error strings (empty = valid).
    """
    props = material.properties
    name = material.name
    cat = material.category
    errs = []

    # All materials need rho
    if props.rho is None:
        errs.append(f"{name}: 'rho' (density) is required")

    # All materials need a way to get speed of sound
    has_v = props.v is not None
    has_c_D = props.c_D is not None
    has_c_E = props.c_E is not None
    if not (has_v or has_c_D or has_c_E):
        errs.append(f"{name}: need at least one of 'v', 'c_D', 'c_E' to determine speed of sound")

    if cat != "piezoelectric":
        return errs

    # Piezoelectric materials additionally need permittivity + coupling
    if props.eps_r_T is None and props.eps_r_S is None:
        errs.append(f"{name}: piezoelectric material needs 'eps_r_T' or 'eps_r_S' (permittivity)")

    has_h = props.h is not None
    has_d = props.d is not None
    has_e = props.e is not None
    if not (has_h or has_d or has_e):
        errs.append(f"{name}: piezoelectric material needs at least one of 'h', 'd', 'e' (coupling constant)")

    # h can only be derived from d if c_D and permittivity are also available
    if not has_h and (has_d or has_e) and not (has_c_D or has_c_E):
        errs.append(f"{name}: deriving 'h' from 'd'/'e' requires 'c_D' or 'c_E' (stiffness)")

    return errs


def derive_properties(material):
    """
    Derive missing properties from available ones.

    Derivation chain for piezoelectric materials:
      1. tan_m from Q_m (if Q_m given)
      2. c_D.imag from c_D.real * tan_m (if c_D.imag not given)
      3. eps_T from eps_r_T * eps_0, with loss from tan_e
      4. h from d via: c_E = c_D*eps_T/(eps_T + c_D*d^2), e = d*c_E, eps_S = eps_T - d^2*c_E, h = e/eps_S
    """
    props = material.properties
    derived = {}

    rho = props.rho.value
    v = props.v.value

    # --- Mechanical loss tangent ---
    # tan_m = 1 / Q_m   (prefer tan_m directly; Q_m accepted as alternative)
    tan_m = get_prop_value(props, "tan_m")
    Q_m = get_prop_value(props, "Q_m")
    if tan_m is None and Q_m is not None and Q_m != 0:
        tan_m = 1.0 / Q_m

    # --- Elastic stiffness c^D (open-circuit) ---
    # c^D* = c^D_real · (1 + j·tan_m)
    # If c_D.imag not provided, derive from: c_D.imag = c_D.real · tan_m
    c_D = get_complex_prop(props, "c_D")
    if c_D is not None:
        if c_D.imag == 0 and tan_m is not None and tan_m != 0:
            c_D = complex(c_D.real, tan_m * c_D.real)
        derived["c_D"] = c_D

    # --- Free (unclamped) permittivity ε^T ---
    # ε^T = ε^T_r · ε_0 · (1 + j·tan_e)
    # ε^T_r is the relative permittivity measured at low frequency on a free sample
    eps_r_T = get_prop_value(props, "eps_r_T")
    tan_e = get_prop_value(props, "tan_e")
    Q_e = get_prop_value(props, "Q_e")
    if tan_e is None and Q_e is not None and Q_e != 0:
        tan_e = 1.0 / Q_e

    eps_T_real = 0.0
    eps_T_imag = 0.0
    if eps_r_T is not None:
        eps_T_real = eps_0 * eps_r_T
    if tan_e is not None and eps_T_real != 0:
        eps_T_imag = -eps_T_real * tan_e
    eps_T = complex(eps_T_real, eps_T_imag)

    # --- Piezoelectric coupling ---
    # Derive h from d if h not given. Uses these relations:
    #   c^E  = c^D · ε^T / (ε^T + c^D · d²)    (closed-form, no iteration)
    #   e    = d · c^E                             (piezoelectric stress constant)
    #   ε^S  = ε^T - d² · c^E                     (clamped permittivity)
    #   h    = e / ε^S                             (piezoelectric stiffness constant)
    # See piezoelectric_relations.md for full derivation.
    h = get_prop_value(props, "h")
    d = get_prop_value(props, "d")

    eps_s = eps_T  # default: ε^S = ε^T (no piezoelectric correction)

    if h is not None:
        # h given directly — still derive ε^S if d and c_D are available
        if d is not None and c_D is not None and eps_T_real != 0:
            c_E = c_D.real * eps_T_real / (eps_T_real + c_D.real * d ** 2)
            eps_s_real = eps_T_real - d ** 2 * c_E
            if tan_e is not None and eps_s_real != 0:
                eps_s_imag = -eps_s_real * tan_e
            else:
                eps_s_imag = 0.0
            eps_s = complex(eps_s_real, eps_s_imag)
    elif d is not None and c_D is not None and eps_T_real != 0:
        # h not given — derive from d
        c_E = c_D.real * eps_T_real / (eps_T_real + c_D.real * d ** 2)
        e = d * c_E
        eps_s_real = eps_T_real - d ** 2 * c_E
        if tan_e is not None and eps_s_real != 0:
            eps_s_imag = -eps_s_real * tan_e
        else:
            eps_s_imag = 0.0
        eps_s = complex(eps_s_real, eps_s_imag)
        h = e / eps_s_real  # h = e / ε^S_real

    # --- Store derived values ---

    # Fundamental
    derived["rho"] = rho
    derived["v"] = v

    # Piezoelectric model
    derived["tan_m"] = tan_m or 0.0
    derived["eps_r_T"] = eps_r_T or 0.0
    derived["tan_e"] = tan_e or 0.0
    derived["eps_s"] = eps_s
    derived["h"] = h or 0.0
    derived["d"] = d or 0.0

    return derived


def build_json(all_materials):
    """Build the JSON output structure."""
    output = {}
    for name, derived in all_materials.items():
        entry = {}
        for key, val in derived.items():
            if isinstance(val, complex):
                entry[key] = {"real": val.real, "imag": val.imag}
            else:
                entry[key] = val
        output[name] = entry
    return output


def build_csv_rows(all_materials):
    """
    Build CSV rows for reference.
    Columns: Material, rho, v, c_D, tan_m, eps_r_T, tan_e, eps_s, h, d
    """
    columns = ["Material", "rho", "v", "c_D", "tan_m", "eps_r_T", "tan_e", "eps_s", "h", "d"]
    rows = [",".join(columns)]

    for name, derived in all_materials.items():
        c_D = derived.get("c_D", 0)
        eps_s = derived.get("eps_s", 0)

        row = [
            name,
            str(derived["rho"]),
            str(derived["v"]) if derived["v"] is not None else "",
            format_complex(c_D),
            str(derived["tan_m"]),
            str(derived["eps_r_T"]),
            str(derived["tan_e"]),
            format_complex(eps_s),
            str(derived["h"]),
            str(derived["d"]),
        ]
        rows.append(",".join(row))

    return "\n".join(rows) + "\n"


def format_complex(val):
    if isinstance(val, complex):
        if val.imag == 0:
            return str(val.real)
        return str(val)
    return str(val)


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)

    yaml_files = sorted(f for f in os.listdir(MATERIALS_DIR) if f.endswith(".yaml") and not f.startswith("_"))

    if not yaml_files:
        print("No YAML files found in materials/")
        sys.exit(1)

    all_materials = {}
    errors = []

    for fname in yaml_files:
        path = os.path.join(MATERIALS_DIR, fname)
        print(f"  Loading {fname}...", end=" ")

        try:
            data = load_yaml(path)
            material = Material(**data)
        except Exception as e:
            print("FAILED (parse)")
            errors.append((fname, str(e)))
            continue

        mat_errors = validate_material(material)
        if mat_errors:
            print("FAILED (validation)")
            errors.extend((fname, e) for e in mat_errors)
            continue

        derived = derive_properties(material)
        all_materials[material.name] = derived
        print("OK")

    if errors:
        print(f"\nValidation failed for {len(errors)} file(s):")
        for fname, err in errors:
            print(f"  {fname}: {err}")
        sys.exit(1)

    # Write JSON
    json_path = os.path.join(BUILD_DIR, "materials.json")
    with open(json_path, "w") as f:
        json.dump(build_json(all_materials), f, indent=2)
    print(f"\n  -> {json_path}")

    # Write CSV
    csv_path = os.path.join(BUILD_DIR, "materials.csv")
    with open(csv_path, "w") as f:
        f.write(build_csv_rows(all_materials))
    print(f"  -> {csv_path}")

    print(f"\nCompiled {len(all_materials)} materials successfully.")


if __name__ == "__main__":
    main()
