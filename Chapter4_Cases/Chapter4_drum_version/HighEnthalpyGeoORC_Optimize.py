# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 2026

@author: flori

OPTIMIZATION: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
    Pymoo optimisation for each working fluid
    and saves the results (optimal points + full evaluation logs)
    The diagram generation is done separately in HighEnthalpyGeoORC_diagrams.py.
    
    Two variables are defined in this script, p_evap & dT_cd (could be fixed).
    Note: 
        - The evaporators UA & pinch are printed to verify feasability a posteriori.
        - The pinch range of the brine evaporator is fixed by the optimizer.
    
    Differential Evolution algorithm could be replaced, seed could be fixed, population
    size & number of generations could be increased.
 
AI advice:
    # Filter out NaNs for convergence failures
    mask = ~np.isnan(log_df["net_power"].values)
    data = log_df.loc[mask].copy() 
    
Note:
    The result selection is improved in the "Final" version, avoiding keeping points
    from the unconstrained results. 
     
"""

import numpy as np
import pandas as pd
from CoolProp.CoolProp import PropsSI as PSI
from pymoo.algorithms.soo.nonconvex.de import DE

from HighEnthalpyGeoORC_Template import HighEnthalpyGeoORC

# -----------------------------------------------------------
# Optimisation Settings & Execution
# -----------------------------------------------------------

T_geo   = 160            # °C
m_geo   = 180            # kg/s
x_steam = 0.1            # [-]
T_inj_constraint = 70    # °C
T_amb = 15               # °C
P_amb = 0.6              # bar
dT_cd = 20               #°C

cooling_fluid = "air"

algorithm = DE(pop_size=40) # the seed can be fixed (seed=n)
termination = ("n_gen", 30)

all_results = {}
summary_rows = []

for fluid in ["n-Pentane", "Isopentane", "Cyclopentane", "n-Butane"]:

    print(f"\n{'='*40}")
    print(f"  Fluid: {fluid}")
    print(f"{'='*40}")

    # p_evap guess based on the working_fluid 
    p_crit = PSI('Pcrit', fluid) / 1e5         # bar
    t_crit = PSI('Tcrit', fluid) - 273.15      # °C
    t_max_evap = min(T_geo - 10, t_crit - 10)   # keep a margin (subcritical)
    t_min_evap = 50                            
    
    p_evap = PSI('P', 'T', (t_max_evap+ 273.15), 'Q', 1, fluid) / 1e5  # bar

    model = HighEnthalpyGeoORC(
        working_fluid       = fluid,
        cooling_fluid        = cooling_fluid,
        geofluidTemperature = T_geo,
        geofluidFlow        = m_geo,
        geofluidVapour      = x_steam,
        evaporationPressure = p_evap,
        T_amb               = T_amb,
        P_amb               = P_amb,
        dT_cd               = dT_cd
    )

    # Dynamical boundaries for p_evap, based on the working_fluid
    p_max_calc = PSI('P', 'T', t_max_evap + 273.15, 'Q', 1, fluid) / 1e5 # bar 
    p_min_calc = PSI('P', 'T', t_min_evap + 273.15, 'Q', 1, fluid) / 1e5 # bar 
    p_hi = min(p_max_calc, 0.90 * p_crit) # Safety value: to ensure subcritical conditions
    p_lo = max(p_min_calc, 1.05)  # Safety value: 1.05 > 1.01325 Bar (1 atm)

    # Variables, Constraints, Objectives, Tracking
    variables = {"p_evap": {"min": float(round(p_lo, 2)), "max": float(round(p_hi, 2))},
                 "dT_cd": {"min": 10, "max": 30}}
    constraints = {"T_injection": {"min": T_inj_constraint},
                   "evap_brine_pinch": {"min": 5, "max": 37}
                   }
    objective = ["net_power"]
    minimize_flags = [False]   # False -> maximise
    kpi = [
    "T_injection", "p_evap", "dT_cd",
    "evap_steam_UA", "evap_brine_UA",
    "evap_steam_pinch", "evap_brine_pinch",
    "thermal_efficiency",
    ]

    # ! In tespy v0.10.2, .optimize() returns a (log_df, pymoo_result) tuple 
    log_df, opt_result = model.optimize(
        algorithm      = algorithm,
        termination    = termination,
        variables      = variables,
        constraints    = constraints,
        objective      = objective,
        minimize_flags = minimize_flags,
        kpi            = kpi,
    )

    # Filter out NaNs for convergence failures
    mask = ~np.isnan(log_df["net_power"].values)
    data = log_df.loc[mask].copy()

    # Export the full evaluation log for this fluid 
    data.to_csv(f"optim_log_{fluid}.csv", index=False)

    # --- Best Unconstrained ---
    best_unc = data.loc[data["net_power"].idxmax()]
    print("\n--- Best (unconstrained) ---")
    print(f"  p_evap      : {best_unc['p_evap']:.3f} bar")
    print(f"  net power   : {best_unc['net_power']:.2f} MW")
    print(f"  T_injection : {best_unc['T_injection']:.2f} °C")
    
    # --- Best Constrained ---
    valid = data[(data["T_injection"] >= T_inj_constraint) &
    (data["evap_brine_pinch"] >= 5) &
    (data["evap_brine_pinch"] <= 37)]
    best_con = None

    if not valid.empty:
        best_con = valid.loc[valid["net_power"].idxmax()]
        print(f"\n--- Best (constrained, T_inj >= {T_inj_constraint:.2f} °C) ---")
        print(f"  p_evap      : {best_con['p_evap']:.3f} bar")
        print(f"  net power   : {best_con['net_power']:.2f} MW")
        print(f"  T_injection : {best_con['T_injection']:.2f} °C")
        print(f"  UA (steam)  : {best_con['evap_steam_UA']:.1f} kW/K")
        print(f"  UA (brine)  : {best_con['evap_brine_UA']:.1f} kW/K")
        print(f"  ttd_min (st): {best_con['evap_steam_pinch']:.2f} °C")
        print(f"  ttd_min (br): {best_con['evap_brine_pinch']:.2f} °C")
        print(f"  eta_th      : {best_con['thermal_efficiency']*100:.2f} %")
    else:
        print(f"\n  [!] No feasible point found with T_injection >= {T_inj_constraint:.2f} °C.")

    all_results[fluid] = {"log": data, "best_unconstrained": best_unc, "best_constrained": best_con}

    # Record the operating point that the diagram script will need to re-solve
    chosen = best_con if best_con is not None else best_unc
    summary_rows.append({
        "fluid":          fluid,
        "cooling_fluid":  cooling_fluid,
        "T_geo":          T_geo,
        "m_geo":          m_geo,
        "x_steam":        x_steam,
        "T_amb":          T_amb,
        "P_amb":          P_amb,
        "p_evap_opt":     chosen["p_evap"],
        "net_power_opt":  chosen["net_power"],
        "T_injection_opt": chosen["T_injection"],
        "constrained":    best_con is not None,
        "dT_cd":          chosen["dT_cd"],  
    })

# -----------------------------------------------------------
# Summary Report
# -----------------------------------------------------------
print(f"\n{'='*80}")
print(f"{'SUMMARY – CONSTRAINED OPTIMUM PER FLUID':^60}")
print(f"{'='*80}")
print(f"{'Fluid':<15} {'p_opt [bar]':>12}{'dT_cd [°C]':>12} {'Net Power [MW]':>16} {'T_inj [°C]':>12}")
print("-" * 80)

for fluid, res in all_results.items():
    bc = res["best_constrained"]
    if bc is not None:
        print(f"{fluid:<15} {bc['p_evap']:>12.3f}{bc['dT_cd']:>12.3f} {bc['net_power']:>16.2f} {bc['T_injection']:>12.2f}")
    else:
        print(f"{fluid:<15} {'N/A':>12} {'N/A':>16} {'N/A':>12}")

# Save the summary table needed by the diagram script
summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv("optimal_points.csv", index=False)
print("\nSaved optimal_points.csv (read by HighEnthalpyGeoORC_diagrams.py)")