# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 2026

@author: flori

EXERGY ANALYSIS: Geothermal ORC Power Plant (High-Enthalpy Two-Phase Resource)

Description:
  - Fuel (E_F)    = net geothermal exergy extracted by the plant: "E_F = E(f0) - E(f6) "  
  - Product (E_P) = net electrical power delivered to the grid: "E_P = E(e6) "        
  - Loss (E_L)    = exergy carried away, unused, by the cooling air: "E_L = E(a2) - E(a0) "  

Note:
    To compute the plant exergetic effiiency by considering the gross geothermal energy input.
    In other words, to treat reinjection as a loss, the ExerPy input data must be adapted as follows:
        
     - Fuel (E_F)    = net geothermal exergy extracted by the plant: "E_F = E(f0) " 
                     =>  "inputs": ['f0'], "outputs":[]
     - Product (E_P) = net electrical power delivered to the grid: "E_P = E(e6) "
                     =>  "inputs": ['e6'], "outputs":[]
     - Loss (E_L)    = exergy carried away: "E_L = E(a2) - E(a0) - E(e6)"
                     =>  "inputs": ['a2'], "outputs":['a0','f6']
     
"""

import matplotlib.pyplot as plt
import numpy as np
from v3_HighEnthalpyGeoORC_Template import HighEnthalpyGeoORC

# -----------------------------------------------------------
# Exergy Analysis
# -----------------------------------------------------------

T_geo = [190, 170, 230]             # °C
x_steam = 0.1           # [-]
m_geo = 180             # kg/s
cooling_fluid = "air"
T_amb = 15              # °C    (state T0)
P_amb = 0.6             # bar   (state p0)
dT_cd = 15              # °C
dT_pp_evap = 8
dT_pp_cond = 10
dT_ap_pre  = 2

# Chosen p_evap per fluid with T_geo maximizing Net Power (during the sweep)
p_evap = [25.28, 21.34, 21.48] # bar

E_D_data = {}  # For the combined plot
FLUIDS = ["n-Pentane", "Isopentane", "Cyclopentane"] 

for i, WF in enumerate(FLUIDS):
    
    p_evap0 = p_evap[i]
    T_geo0  = T_geo[i]

    orc = HighEnthalpyGeoORC(
        working_fluid       = WF,
        cooling_fluid        = cooling_fluid,
        geofluidTemperature = T_geo0,
        geofluidFlow        = m_geo,
        geofluidVapour      = x_steam,
        evaporationPressure = p_evap0,
        T_amb               = T_amb,
        P_amb               = P_amb,
        dT_cd               = dT_cd,
        dT_pp_evap          = dT_pp_evap,
        dT_pp_cond          = dT_pp_cond,
        dT_ap_pre           = dT_ap_pre,
    )
    
    print(f"\n{'='*60}")
    print(f"{'THERMO ANALYSIS':^60}")
    print(f"{'='*60}")
    orc.nw.print_results()
    print(f"\nNet power   = {orc.get_parameter('net_power'):.3f} MW")
    print(f"T_injection = {orc.get_parameter('T_injection'):.2f} degC")
    print(f"p_evap      = {orc.get_parameter('p_evap'):.2f} bar")
    orc.save_design()
    
    # --- FUEL|PRODUCT|LOSS definitions ---
    fuel = {"inputs": ['f0'], "outputs": ['f6']} 
    product = {"inputs": ['e6'], "outputs": []}
    loss = {"inputs": ['a2'], "outputs": ['a0']} 

    exergy_kwargs = {"Tamb": T_amb, "pamb": P_amb, "E_F": fuel, "E_P": product, "E_L": loss}

    ean = orc.run_exergy_analysis(**exergy_kwargs)
    print(f"\n{'='*60}")
    print(f"{'EXERGY ANALYSIS':^60}")
    print(f"{'='*60}")
    ean.print_exergy_summary()
    
  
    # --- Verification ---
    """
    Exergy efficiencies the way Zhao et al. (2022) define it in Eq. 9 to 13.
    [See the thesis bibliography]
    """
    E_f0_kW = ean.connections['f0']['E'] / 1000          # ! Exerpy stores exergy in W
    E_f6_kW = ean.connections['f6']['E'] / 1000          
    net_power_kW = orc.get_parameter('net_power') * 1000 # HighEnthalpyGeoORC stores e-power in MW
    E_wf_in = ean.connections['r3']['E'] / 1000          
    E_wf_out = ean.connections['r9']['E'] / 1000        
    Delta_E_O = E_wf_out - E_wf_in
    
    eta_plant_II = net_power_kW / E_f0_kW
    eta_Geothermal_Utilization_II = ( E_f0_kW - E_f6_kW) / E_f0_kW
    eta_Geothermal_Heating_II =  Delta_E_O / ( E_f0_kW - E_f6_kW)
    eta_cycle_II = net_power_kW/Delta_E_O
    
    print(f"\neta_exerpy (net-extracted-fuel, Exerpy) = {ean.epsilon:.2%}")
    print(f"eta_plant (Zhao et al.)   = {eta_plant_II:.2%}")
    print(f"eta_Geo_Utilization (Zhao et al.)   = {eta_Geothermal_Utilization_II:.2%}")
    print(f"eta_Geo_Heating (Zhao et al.)   = {eta_Geothermal_Heating_II:.2%}")
    print(f"eta_Cycle (Zhao et al.)   = {eta_cycle_II:.2%}")
    
    
    # --- DataFrames from Exerpy ---
    df_comp, df_material, df_power = ean.exergy_results()
    
    # --- Extract component E_D / running E_F for the combined comparison plot ---
    df_comp_f = df_comp[(df_comp["Component"] != "TOT") & df_comp["E_F [kW]"].notna()].copy()

    # --- Embedded WATERFALL PLOT ---
    fig, ax = ean.plot_exergy_waterfall(title=f"{WF} ORC Exergy Analysis")
    plt.tight_layout()
    fig.savefig(f"{WF}_waterfall.svg")
    plt.close()

# -----------------------------------------------------------
# Combined component exergy-destruction comparison (% of E_F)
# Note: Based on TESPy v0.10.2 updated Tutorials
# -----------------------------------------------------------

    comps = ["E_F"]
    E_D_list = [0]
    running = ean.E_F          # W
    E_P_list = [running]

    for _, row in df_comp_f.iterrows():
        e_d = row["E_D [kW]"] * 1e3   # W
        if e_d > 1:
            comps.append(row["Component"])
            E_D_list.append(e_d)
            running -= e_d
            E_P_list.append(running)
    
    comps.append("Exergetic loss")
    E_L_step = running - ean.E_P   
    E_D_list.append(E_L_step)
    running = ean.E_P              
    E_P_list.append(running)
    
    comps.append("E_P")
    E_D_list.append(0)
    E_P_list.append(running)

    E_D_data[WF] = {"comps": comps, "E_D": E_D_list, "E_P": E_P_list, "T_geo": T_geo0, "p_evap": p_evap0}

    
# -- Plot ---
fig, axs = plt.subplots(1, len(FLUIDS), figsize=(6.5 * len(FLUIDS), 6),
                         constrained_layout=True, sharex=True)

for col, WF in enumerate(FLUIDS):
    comps = E_D_data[WF]["comps"]
    E_D_arr = np.array(E_D_data[WF]["E_D"])
    E_P_arr = np.array(E_D_data[WF]["E_P"])
    E_F_tot = E_P_arr[0]                     # total fuel exergy for this fluid
    y_pos = np.arange(len(comps))
    colors = ["#3a9dce"] + ["#f08e2b"] * (len(comps) - 2) + ["#db5252"]

    E_P_pct = E_P_arr / E_F_tot * 100
    E_D_pct = E_D_arr / E_F_tot * 100
    is_loss_row = np.array([c == "Exergetic loss" for c in comps])
    
    ax = axs[col]
    ax.barh(y_pos, E_P_pct, align="center", color=colors)
    # internal component destruction (green)
    ax.barh(y_pos, np.where(is_loss_row, 0, E_D_pct), align="center", left=E_P_pct,
            color="#6ed880", label="E_D (destruction)" if col == 0 else None)
    # exergetic loss (grey)
    ax.barh(y_pos, np.where(is_loss_row, E_D_pct, 0), align="center", left=E_P_pct,
            color="#9e9e9e", label="E_L (loss)" if col == 0 else None)

    for pos, ep, ed in zip(y_pos, E_P_pct, E_D_pct):
        # exergy remaining right after this stage, inside the bar
        ax.text(ep - 1.5, pos, f"{ep:.1f}%", va="center", ha="right",
                 fontsize=8, fontweight="bold", color="white")
        
        if ed > 0:
            ax.text(ep + ed + 1.5, pos, f"-{ed:.1f}%", va="center", ha="left",
                     fontsize=8, color="#555555")

    ax.set_xlabel(r"$\epsilon$ [%]")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(comps)
    ax.set_title(f"{WF}\nT_geo={E_D_data[WF]['T_geo']:.0f}°C, p_evap={E_D_data[WF]['p_evap']:.2f} bar")
    ax.invert_yaxis()

axs[0].set_xlim(0, 118)  
fig.suptitle("Component Exergy Destruction (% of Fuel Exergy)", fontsize=14)
fig.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.06))
fig.savefig("Combined_ExergyDestruction_pct.svg", bbox_inches="tight")
plt.close()