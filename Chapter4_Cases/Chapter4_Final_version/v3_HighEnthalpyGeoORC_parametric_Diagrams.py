# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 2026

@author: flori

PARAMETRIC OPTIMIZATION DIAGRAMS: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
    Diagram script that reads results_Tgeo_sweep.csv (produced by
    HighEnthalpyGeoORC_parametric_Optimize_parallel.py). The diagrams are:

    1. Optimal evaporation temperature vs. T_geo
    2. Net power output vs. T_geo
    3. Reinjection temperature (at the optimum) vs. T_geo
    4. Optimal pressure ratio p_evap / p_crit vs. T_geo

    All the optimum points are subcritical (the search is bounded by
    0.9 * p_crit or the evap_pinch), so the saturation temperature is always 
    defined and the original T_evap_from_p helper is kept as it was.
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import transforms
from CoolProp.CoolProp import PropsSI as PSI

FLUIDS = ["n-Pentane", "Isopentane", "Cyclopentane", "n-Butane"]

T_inj_values = [65, 75]

# True = only pymoo feasible points; False = all generated points
ONLY_FEASIBLE = True

COLORS = {"n-Pentane": "tab:green", "Isopentane": "tab:blue",
          "Cyclopentane": "tab:red", "n-Butane": "tab:orange"}

# Distinct marker shapes per fluid 
MARKERS = {"n-Pentane": "o", "Isopentane": "s",
           "Cyclopentane": "^", "n-Butane": "D"}

# Critical temperatures in °C for each fluid
T_CRIT = {fluid: PSI("Tcrit", fluid) - 273.15 for fluid in FLUIDS}


def add_tcrit_marks(ax, fluids):
    """
    Dashed vertical line at each fluid's T_crit (as before) plus a
    small marker sitting on the x-axis, same colour/shape as that
    fluid's curve 
    
    """
    trans = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    for fluid in fluids:
        if fluid not in T_CRIT:
            continue
        ax.axvline(T_CRIT[fluid], color=COLORS[fluid], linestyle="--",
                   linewidth=1.2, alpha=0.7, zorder=1)
        ax.plot(T_CRIT[fluid], 0, marker=MARKERS[fluid],
                color=COLORS[fluid], transform=trans, clip_on=False,
                markersize=7, markeredgecolor="black", markeredgewidth=0.5,
                linestyle="none", zorder=1) # Zorder chose the level of symbols


def plot_vs_Tgeo(df, y_col, y_label, title, hline_per_panel=None):
    """
    hline_per_panel: optional dict {T_inj: value} to draw a dashed
    horizontal reference line per panel (used for the T_inj constraint
    on the reinjection-temperature plot).
    
    """
    fig, axes = plt.subplots(1, len(T_inj_values),
                             figsize=(6 * len(T_inj_values), 5),
                             sharey=True)
    if len(T_inj_values) == 1:
        axes = [axes]

    for ax, T_inj in zip(axes, T_inj_values):
        sub = df[df["T_inj"] == T_inj]
        if ONLY_FEASIBLE and "constrained" in sub.columns:
            sub = sub[sub["constrained"]]

        for fluid in FLUIDS:
            fsub = sub[sub["fluid"] == fluid].sort_values("T_geo")
            if fsub.empty:
                continue
            ax.plot(fsub["T_geo"], fsub[y_col], marker=MARKERS[fluid],
                    color=COLORS[fluid], linewidth=1.8, markersize=6,
                    label=fluid)

        if hline_per_panel is not None and T_inj in hline_per_panel:
            ax.axhline(hline_per_panel[T_inj], color="grey", linestyle="--",
                       linewidth=1.2, label=f"T_inj constraint ({T_inj} °C)")

        add_tcrit_marks(ax, FLUIDS)

        ax.set_title(f"T_inj = {T_inj} °C", fontsize=13)
        ax.set_xlabel("T_geo [°C]", fontsize=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9)

    axes[0].set_ylabel(y_label, fontsize=12)
    fig.suptitle(title, fontsize=15)
    fig.text(0.5, -0.02,
             "Dashed vertical lines / axis markers: each fluid's critical "
             "temperature (same colour/marker as its curve).",
             ha="center", fontsize=9, style="italic")
    fig.tight_layout()
    return fig


def T_evap_from_p(fluid, p_bar):
    """Saturation temperature (°C) of the working fluid at p_evap_opt."""
    return PSI("T", "P", p_bar * 1e5, "Q", 1, fluid) - 273.15


# =============================================================================
# Load data
# =============================================================================
df_Tgeo = pd.read_csv("results_Tgeo_sweep.csv")

# x_steam is fixed for the whole pipeline (value from the data)
x_steam_fixed = df_Tgeo["x_steam"].iloc[0] if "x_steam" in df_Tgeo.columns else "?"

df_Tgeo["T_evap_opt"] = [
    T_evap_from_p(fluid, p) for fluid, p in zip(df_Tgeo["fluid"], df_Tgeo["p_evap_opt"])
]

# =============================================================================
# 1. Optimal evaporation temperature vs T_geo
# =============================================================================
fig1 = plot_vs_Tgeo(
    df_Tgeo, "T_evap_opt",
    y_label="Optimal evaporation temperature [°C]",
    title=f"Optimal evaporation temperature vs. T_geo (x_steam = {x_steam_fixed})",
)

# =============================================================================
# 2. Net power output vs T_geo
# =============================================================================
fig2 = plot_vs_Tgeo(
    df_Tgeo, "net_power_opt",
    y_label="Net power output [MW]",
    title=f"Net power output vs. T_geo (x_steam = {x_steam_fixed})",
)

# =============================================================================
# 3. Actual reinjection temperature vs T_geo (vs. the T_inj constraint)
# =============================================================================
fig3 = plot_vs_Tgeo(
    df_Tgeo, "T_injection_opt",
    y_label="Reinjection temperature [°C]",
    title=f"Reinjection temperature vs. T_geo (x_steam = {x_steam_fixed})",
    hline_per_panel={T_inj: T_inj for T_inj in T_inj_values},
)

figs = [(fig1, "Tevap_vs_Tgeo"), (fig2, "NetPower_vs_Tgeo"),
        (fig3, "Treinj_vs_Tgeo")]

# =============================================================================
# 4. Optimal pressure level vs T_geo (how close to the subcritical ceiling)
# =============================================================================
if "p_ratio_crit" in df_Tgeo.columns:
    fig4 = plot_vs_Tgeo(
        df_Tgeo, "p_ratio_crit",
        y_label="Optimal p_evap / p_crit [-]",
        title=f"Optimal pressure level vs. T_geo (x_steam = {x_steam_fixed})",
        hline_per_panel={T_inj: 0.9 for T_inj in T_inj_values},
    )
    figs.append((fig4, "PressureRatio_vs_Tgeo"))

for fig, name in figs:
    fig.savefig(f"./{name}.svg", bbox_inches="tight")

plt.show()
print("\nAll parametric diagrams generated.")
