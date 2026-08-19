# Defays2026_Polimi

General-purpose geothermal surface plant simulation model using TESPy (ORCs).
Developed for a Master's thesis at the University of Liège (ULiège), during
an internship at Politecnico di Milano (Polimi).

## Overview

This repository contains a TESPy-based simulation and optimization framework
for geothermal Organic Rankine Cycle (ORC) power plants, developed
incrementally across three thesis chapters:

- **Chapter 1** — building-block validation models (heat pump, fan, heat
  exchanger comparison, ORC subsystem interface).
- **Chapter 2** — theoretical/literature background; no code associated with
  this chapter, so it is not represented in this repository.
- **Chapter 3** — low-enthalpy ORC case studies.
- **Chapter 4** — high-enthalpy two-phase geothermal ORC: the core thesis
  model, including working-fluid selection, single-point optimization,
  parametric sweeps across resource temperatures, and exergy analysis.

## Repository structure

```
Chapter1_Cases/
├── Fan/                   # Fan model
├── HP/                    # Heat pump model, pymoo optimization, exergy analysis
├── HXs_comparison/        # Heat exchanger model comparison
└── Subsytem_Interface/    # ORC preheater/recuperator subsystem tests

Chapter3_Cases/
├── Case1/                 # Low-enthalpy ORC, inputs from documentation
├── Case2/                 # PropsSI vs. TESPy comparison
└── Case3/                 # Low-binary ORC test

Chapter4_Cases/
├── Chapter4_Final_version/   # Final high-enthalpy geothermal ORC model
│   ├── v3_HighEnthalpyGeoORC_Template.py            # Simulation template
│   ├── v3_HighEnthalpyGeoORC_Optimize.py            # Single-point optimization (pymoo)
│   ├── v3_HighEnthalpyGeoORC_Parametric_Optimize_Parallel.py  # Parametric sweep over T_geo
│   ├── v3_HighEnthalpyGeoORC_Exergy.py              # Exergy analysis (ExerPy)
│   ├── v3_HighEnthalpyGeoORC_Diagrams.py            # Single-case diagrams
│   ├── v3_HighEnthalpyGeoORC_parametric_Diagrams.py # Parametric sweep diagrams
│   ├── CSVs/                                        # Optimization logs and results
│   └── Diagrams/                                    # Generated SVG figures
├── Chapter4_drum_version/    # Earlier drum-based architecture (kept for reference)
└── chapter4_fluids/          # Working-fluid selection study

functions/
├── Fluprodia_diagrams_f.py   # Fluid property (T-s, log p-h) diagram helpers
└── HX_diagrams_f.py          # Heat exchanger Q-T diagram helpers
```

## Requirements

Python 3.12. **TESPy's API changed across the thesis's development
timeline (v0.9.12 → v0.10.2), so each chapter needs its own TESPy version**
— there isn't a single `requirements.txt` that works for the whole
repository. Install the one matching the chapter you want to run:

| Chapter | TESPy version | Requirements file |
|---|---|---|
| Chapter 1 | 0.9.16 *(reconstructed from memory — verify before relying on it)* | `Chapter1_Cases_requirements.txt` |
| Chapter 3 | 0.9.14 | `Chapter3_Cases_requirements.txt` |
| Chapter 4 (main model) | 0.10.2 | `requirements.txt` |

```bash
# Chapter 4 (main model)
pip install -r requirements.txt

# Chapter 1
pip install -r Chapter1_Cases_requirements.txt

# Chapter 3
pip install -r Chapter3_Cases_requirements.txt
```

Since the TESPy versions are incompatible with each other, use a separate
virtual environment per chapter if you need to run more than one.

Key dependencies: [TESPy](https://tespy.readthedocs.io/) (thermal system
simulation), [ExerPy](https://github.com/oemof/exerpy) (exergy analysis),
[CoolProp](http://www.coolprop.org/) (fluid properties),
[pymoo](https://pymoo.org/) (multi-objective/differential-evolution
optimization), [fluprodia](https://fluprodia.readthedocs.io/) (fluid
property diagrams, Chapter 1 only).

## Usage — Chapter 4 (main model)

The scripts in `Chapter4_Cases/Chapter4_Final_version/` are meant to be run
in this order:

1. `v3_HighEnthalpyGeoORC_Template.py` — defines and solves the base plant
   model for a single operating point.
2. `v3_HighEnthalpyGeoORC_Optimize.py` — single-point differential-evolution
   optimization (`p_evap`, `dT_cd`) for a given resource temperature.
3. `v3_HighEnthalpyGeoORC_Parametric_Optimize_Parallel.py` — repeats the
   optimization across a sweep of geothermal resource temperatures.
4. `v3_HighEnthalpyGeoORC_Exergy.py` — exergy analysis and component-level
   exergy-destruction comparison across working fluids.
5. `v3_HighEnthalpyGeoORC_Diagrams.py` / `v3_HighEnthalpyGeoORC_parametric_Diagrams.py`
   — generate the SVG figures used in the thesis.

## Author

Florian Defays — University of Liège (ULiège), 2026.

## License

No open-source license is attached to this repository. Under the
traineeship agreement between the University of Liège and Politecnico di
Milano — respectively "the University" and "the Host Institution" in the
clause below — ownership of the results obtained during this internship
follows the Host Institution's ownership option:

> The results which are obtained by the student trainee during their
> traineeship within the Host Institution will belong to the Host
> Institution, which will have exclusive rights to use them.
> Notwithstanding the provisions of Article 4, however, the University will
> retain the right to use these results for scientific or teaching
> purposes, and will retain under all circumstances, exclusive ownership of
> the knowledge previously acquired in the area in question. Notwithstanding
> the above, the University will retain ownership of the methods and
> know-how developed by the academic supervisor at the University and/or
> the student trainee at the time of this agreement.

Accordingly, the results in this repository belong to Politecnico di Milano
(the Host Institution). This repository is made public for visibility
purposes only; it does not grant any reuse, redistribution, or modification
rights to third parties.

This ownership applies to the code, scripts, and results authored during
the internship. It does not affect the separate open-source licenses of the
third-party libraries this project depends on (TESPy, CoolProp, ExerPy,
fluprodia — MIT; pymoo — Apache-2.0), which remain the property of their
respective authors under their own license terms.
