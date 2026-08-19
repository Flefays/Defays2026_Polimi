# -*- coding: utf-8 -*-
"""
Created on Wed Aug  5 16:02:39 2026

@author: flori

FLUID SELECTION: Saturation curves for hydrocarbons.
 
Description:
    Saturation curves T-s plot and critical points for several hydrocarbons with CoolProp.
    It uses the same entropy reference to display all the curves. 
    
AI Usage:
    Asked the AI to harvest & refont the entropy reference for each fluid.     
    try/except method.
    
"""

import matplotlib.pyplot as plt
import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import AbstractState

# -----------------------------------------------------------
# Plot font, axes & sizes
# -----------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 14,
    "axes.labelsize": 16,
    "axes.linewidth": 1.1,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
})

# Fluid names: offset positioning relative to critical point: (delta_s, delta_T) 
fluids = {
    "Propane": {
        "name": "propane",
        "color": "#e7298a",
        "offset": (30, 10),
    },
    "Isobutane": {
        "name": "i-butane",
        "color": "#2b5c8f",
        "offset": (30, -12),
    },
    "n-Butane": {
        "name": "n-butane",
        "color": "#e6ab02",
        "offset": (-200, -12),
    },
    "Isopentane": {
        "name": "i-pentane",
        "color": "#36827f",
        "offset": (-210, -12),
    },
    "n-Pentane": {
        "name": "n-pentane",
        "color": "#d95f02",
        "offset": (35, -15),
    },
    "Cyclopentane": {
        "name": "Cyclopentane",
        "color": "#7570b3",
        "offset": (-250, -12),
    },
}

crit_data = {}  # will hold the critical values for the table {label: (Tcrit_C, Pcrit_bar)}

fig, ax = plt.subplots(figsize=(9, 6.5))

# -----------------------------------------------------------
# Calculations & Plotting
# -----------------------------------------------------------
for fluid_id, data in fluids.items():
    AS = AbstractState("HEOS", fluid_id)
    Tcrit = AS.T_critical()  # K
    Ttriple = AS.Ttriple()   # K
    Pcrit = AS.p_critical()  # Pa
    crit_data[data["name"]] = (Tcrit - 273.15, Pcrit / 1e5)  # conversion to °C, bar & storage

    T_ref = 273.15  # Reference baseline: 0 °C
    T_min = max(Ttriple + 0.5, T_ref)
    T_max = Tcrit - 0.4
    T_vals = np.linspace(T_min, T_max, 400)

    # Determine reference entropy so s_liq(0 °C) = 0 J/kg/K
    try:
        AS.update(CP.QT_INPUTS, 0, T_ref)
        s_ref = AS.smass()
    except Exception:
        AS.update(CP.QT_INPUTS, 0, T_min)
        s_ref = AS.smass()

    s_liq, s_vap, T_valid = [], [], []

    for Ti in T_vals:
        try:
            # Saturated liquid entropy
            AS.update(CP.QT_INPUTS, 0, Ti)
            s_l = AS.smass() - s_ref

            # Saturated vapor entropy
            AS.update(CP.QT_INPUTS, 1, Ti)
            s_v = AS.smass() - s_ref

            s_liq.append(s_l)
            s_vap.append(s_v)
            T_valid.append(Ti - 273.15)
        except (ValueError, RuntimeError):
            continue

    s_liq = np.array(s_liq)
    s_vap = np.array(s_vap)
    T_C = np.array(T_valid)

    # Estimate critical point entropy
    try:
        AS.update(CP.QT_INPUTS, 0, Tcrit - 0.05)
        s_crit = AS.smass() - s_ref
    except Exception:
        s_crit = (s_liq[-1] + s_vap[-1]) / 2.0

    Tcrit_C = Tcrit - 273.15

    # Connect liquid line -> critical apex -> vapor line
    s_dome = np.concatenate([s_liq, [s_crit], s_vap[::-1]])
    T_dome = np.concatenate([T_C, [Tcrit_C], T_C[::-1]])

    # Plot saturation dome
    ax.plot(s_dome, T_dome, color=data["color"], linewidth=2.0)

    # Direct color-matched label placed near critical point
    ds, dT = data["offset"]
    ax.text(
        s_crit + ds,
        Tcrit_C + dT,
        data["name"],
        color=data["color"],
        fontsize=11,
        fontweight="bold",
        va="center",
    )

# -----------------------------------------------------------
# Axis Formatting
# -----------------------------------------------------------
ax.set_xlabel("Entropy j/kg/K")
ax.set_ylabel("Temperature °C")
ax.set_xlim(0, 2000)
ax.set_ylim(0, 260)
ax.set_xticks(np.arange(0, 2001, 200))
ax.set_yticks(np.arange(0, 261, 50))
ax.grid(True, linestyle="-", alpha=0.35, color="gray")

plt.tight_layout()
plt.savefig("Ts_working_fluids.png", dpi=300, bbox_inches="tight")
plt.show()

# -----------------------------------------------------------
# Critical Point Table
# -----------------------------------------------------------
print(f"{'Fluid':<15}{'Tcrit [°C]':>12}{'Pcrit [bar]':>14}")
print("-" * 41)
for name, (Tc, Pc) in crit_data.items():
    print(f"{name:<15}{Tc:>12.2f}{Pc:>14.2f}")

