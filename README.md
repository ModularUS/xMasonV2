# xMasonV2

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22117703.svg)](https://doi.org/10.5281/zenodo.22117703)

A simulation library for cascaded (multi-layer) piezoelectric ultrasound
transducers. It predicts the electrical impedance of a layer stack across a
frequency band using a transfer-matrix model, and derives RF quantities
(S11, return loss, SWR) and a Smith chart from it. Stacks, materials, and
outputs are defined in YAML.

## Install

```bash
git clone https://github.com/ModularUS/xMasonV2
cd xMasonV2
pip install -r requirements.txt   # Python 3.10+
```

## Usage

Define a stack in a YAML config (see `simulation_scripts/config/pvdfstack.yaml`),
then run:

```bash
python simulation_scripts/run_local_yamlsim.py
```

Each run writes a timestamped directory under `scratch/` containing a results
CSV, interactive Plotly plots, a Smith chart PNG, and a copy of the config.

### Config format

All quantities are SI (metres, Hz, Ohm).

```yaml
diameter: 10.0e-3                  # m  (or: side_length / area)
connection: parallel-alternating   # parallel | series | parallel-alternating
backing-material: Air
transmission-material: Air
source-impedance: 50               # Ohm (optional, default 50)

frequency-band:
  min: 0.5e6                       # Hz
  max: 50.0e6                      # Hz
  step: 0.01e6                     # Hz (optional)

output:
  - impedance
  - Z-real-imag

transducer:                        # thickness in metres; polarization: up | down
  - {material: "Ag",          thickness: 4.0e-6}
  - {material: "P(VDF-TrFE)", thickness: 110.0e-6, polarization: up}
  - {material: "Ag",          thickness: 4.0e-6}
  - {material: "P(VDF-TrFE)", thickness: 110.0e-6, polarization: down}
  - {material: "Ag",          thickness: 4.0e-6}
```

**Wiring schemes** — `series`, `parallel`, or `parallel-alternating` (parallel
connection with alternating layer polarities).

**Polarization** — `up` (default) or `down`. Only the *relative* polarization
between layers matters; `up, down, up` is equivalent to `down, up, down`.

### Outputs

| Key | Quantity |
|-----|----------|
| `impedance` | Complex electrical impedance Z(f) |
| `Z-real-imag` | Real and imaginary parts of Z |
| `S11` | Reflection coefficient magnitude |
| `S11-real-imag` | S11 real and imaginary parts |
| `S11-phase` | S11 phase (degrees) |
| `return-loss` | Return loss, 20·log10(\|S11\|) [dB] |
| `SWR` | Standing wave ratio |

A Smith chart PNG is also produced when `impedance` is requested.

## Material database

Materials are individual YAML files in `material_database/materials/`, compiled
into a registry the simulation loads. Each material specifies density, speed of
sound (or elastic stiffness), and — for piezoelectrics — the coupling constant,
permittivity, and loss factors; see `materials/_template.yaml` for the schema.

Available: `Ag`, `Air`, `P-53`, `P(VDF-TrFE)`, `Transfertape`, `Water`.

Add a material by creating a YAML file and recompiling:

```bash
python material_database/scripts/compile.py   # -> build/materials.{json,csv}
```

## Layout

```
app/
  models/      layer.py, matrices.py, transducer.py   transfer-matrix physics
  pipeline/    config_parser.py, simulation.py, results_io.py, plotting.py
  analysis/    rf_utils.py                             scikit-rf bridge, Smith chart
  utils/       logger.py
material_database/
  materials/   per-material YAML sources
  build/       compiled materials.{json,csv}
  scripts/     compile.py
  src/         loader.py, models.py
simulation_scripts/
  run_local_yamlsim.py                                 YAML batch runner
  config/      pvdfstack.yaml
```

## Method

Each layer is represented as a 4×4 transfer matrix relating force, velocity,
voltage, and current. The multi-layer and alternating-parallel formulation
follows Almohimeed [1], building on Sittig's transfer-matrix parameters [2] and
Mason's equivalent-circuit model [3]. Layers are cascaded by matrix
multiplication, backing and transmission boundary conditions are applied, and
the system is solved for electrical impedance versus frequency.

## References

[1] I. Almohimeed, "Design and construction of a double-layer PVDF wearable
ultrasonic sensor for the quantitative assessment of muscle contractile
properties," Carleton University, 2021.

[2] E. Sittig, "Transmission parameters of thickness-driven piezoelectric
transducers arranged in multilayer configurations," IEEE Transactions on Sonics
and Ultrasonics, vol. 14, no. 4, pp. 167-174, 1967.

[3] W. Mason, "Electromechanical Transducers and Wave Filters," Bell Telephone
Laboratories series, D. Van Nostrand Company, 1948.

## License

Apache License 2.0 — see [LICENSE](LICENSE).