# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 2026

@author: flori

PARAMETRIC OPTIMIZATION: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
    A sweep is run and saved to CSV (read afterwards by
    HighEnthalpyGeoORC_parametric_diagrams.py):

    -T_geo sweep: for each fluid and each temperature re-injection constraint, 
    it optimises net power over a range of geofluid temperatures (T_geo), 
    at a fixed steam fraction, and fixed dT_cd.
     -> results_Tgeo_sweep.csv

Each optimisation is a full pymoo run (pop_size x n_gen evaluations) !!!

In a more recent script, this has been adapted for parallel resolution.
"""

import numpy as np
import pandas as pd

from CoolProp.CoolProp import PropsSI as PSI
from pymoo.algorithms.soo.nonconvex.de import DE

from HighEnthalpyGeoORC_Template import HighEnthalpyGeoORC

# -----------------------------------------------------------------------------
# Sweep settings (can be adjusted)
# -----------------------------------------------------------------------------
FLUIDS = ["n-Pentane", "Isopentane", "Cyclopentane", "n-Butane"]

T_geo_range = np.arange(180, 250 + 1, 10)     # 180, 190, ..., 250 °C
T_inj_values = [70, 100]                      # °C

x_steam_default = 0.1                          
m_geo = 180             # kg/s
cooling_fluid = "air"
T_amb = 15              # degC
P_amb = 0.6             # bar
dT_cd = 20              # °C

algorithm = DE(pop_size=50)
termination = ("n_gen", 80)


# -----------------------------------------------------------------------------
# Optimisation routine
# -----------------------------------------------------------------------------
def optimize_case(fluid, T_geo, x_steam, T_inj):
    """
    Run an optimisation for a given fluid / T_geo / x_steam / T_inj
    Returns a dict with the chosen (constrained if feasible, else
    unconstrained) optimal point, or None if nothing could be evaluated.
    """

    # p_evap guess based on the working_fluid (first "design" run)
    p_crit = PSI('Pcrit', fluid) / 1e5          # bar
    t_crit = PSI('Tcrit', fluid) - 273.15       # °C
    t_max_evap = min(T_geo - 10, t_crit - 10)   # keep a margin (subcritical)
    t_min_evap = 50

    p_evap = PSI('P', 'T', (t_max_evap + 273.15), 'Q', 1, fluid) / 1e5

    try:
        model = HighEnthalpyGeoORC(
            working_fluid       = fluid,
            cooling_fluid        = cooling_fluid,
            geofluidTemperature = T_geo,
            geofluidFlow        = m_geo,
            geofluidVapour      = x_steam,
            evaporationPressure = p_evap,
            T_amb               = T_amb,
            P_amb               = P_amb,
            dT_cd               = dT_cd,
        )
    except Exception as e:
        print(f" [!] initial design solve failed: {e}")
        return None

    p_max_calc = PSI('P', 'T', t_max_evap + 273.15, 'Q', 1, fluid) / 1e5 # bar
    p_min_calc = PSI('P', 'T', t_min_evap + 273.15, 'Q', 1, fluid) / 1e5 # bar
    p_hi = min(p_max_calc, 0.90 * p_crit) 
    p_lo = max(p_min_calc, 1.05)

    if p_hi <= p_lo:
        print(f" [!] infeasible p_evap bounds (p_lo={p_lo:.2f} >= p_hi={p_hi:.2f})")
        return None

    variables = {"p_evap": {"min": float(round(p_lo, 2)), "max": float(round(p_hi, 2))}}
    constraints = {"T_injection": {"min": T_inj}}
    objective = ["net_power"]
    minimize_flags = [False]
    kpi = ["T_injection", "p_evap"]

    try:
        log_df, opt_result = model.optimize(
            algorithm      = algorithm,
            termination    = termination,
            variables      = variables,
            constraints    = constraints,
            objective      = objective,
            minimize_flags = minimize_flags,
            kpi            = kpi,
        )
    except Exception as e:
        print(f"  [!] optimisation failed: {e}")
        return None

    mask = ~np.isnan(log_df["net_power"].values)
    data = log_df.loc[mask].copy()
    if data.empty:
        print("  [!] no converged points at all")
        return None

    best_unc = data.loc[data["net_power"].idxmax()]
    valid = data[data["T_injection"] >= T_inj]
    best_con = valid.loc[valid["net_power"].idxmax()] if not valid.empty else None

    chosen = best_con if best_con is not None else best_unc
    return {
        "p_evap_opt":      chosen["p_evap"],
        "net_power_opt":   chosen["net_power"],
        "T_injection_opt": chosen["T_injection"],
        "constrained":     best_con is not None,
    }


# -----------------------------------------------------------------------------
# Sweep: T_geo (get p_evap, net_power, T_re-injection)
# -----------------------------------------------------------------------------
rows_Tgeo = []
n_cases = len(FLUIDS) * len(T_inj_values) * len(T_geo_range)
i_case = 0

for fluid in FLUIDS:
    for T_inj in T_inj_values:
        for T_geo in T_geo_range:
            i_case += 1
            print(f"[T_geo sweep {i_case}/{n_cases}] fluid={fluid}  "
                  f"T_geo={T_geo}C  T_inj={T_inj}°C")

            result = optimize_case(fluid, float(T_geo), x_steam_default, T_inj)
            if result is None:
                continue

            rows_Tgeo.append({
                "fluid": fluid, "T_inj": T_inj, "T_geo": T_geo,
                "x_steam": x_steam_default, "m_geo": m_geo,
                "cooling_fluid": cooling_fluid, "T_amb": T_amb, "P_amb": P_amb,
                **result,
            })

pd.DataFrame(rows_Tgeo).to_csv("results_Tgeo_sweep.csv", index=False)
print("\nSaved results_Tgeo_sweep.csv")
