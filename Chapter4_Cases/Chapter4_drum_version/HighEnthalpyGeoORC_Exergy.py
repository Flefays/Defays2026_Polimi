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
from HighEnthalpyGeoORC_Template import HighEnthalpyGeoORC

# -----------------------------------------------------------
# Exergy Analysis
# -----------------------------------------------------------

T_geo = 160             # degC
x_steam = 0.1           # [-]
m_geo = 180             # kg/s
cooling_fluid = "air"
T_amb = 15              # degC  (state T0)
P_amb = 0.6             # bar   (state p0)
dT_cd = 20              #°C

# Chosen p_evap per fluid
p_evap = [13.89] # bar

for i, WF in enumerate(["n-Pentane"]):

    p_evap0 = p_evap[i]
    
    orc = HighEnthalpyGeoORC(
        working_fluid       = WF,
        cooling_fluid        = cooling_fluid,
        geofluidTemperature = T_geo,
        geofluidFlow        = m_geo,
        geofluidVapour      = x_steam,
        evaporationPressure = p_evap0,
        T_amb               = T_amb,
        P_amb               = P_amb,
        dT_cd               = dT_cd,
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
    loss = {"inputs": ['a2'], "outputs": ['a0','f6']} 

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
    E_wf_out = ean.connections['r11']['E'] / 1000        
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

    # --- Embedded WATERFALL PLOT ---
    fig, ax = ean.plot_exergy_waterfall(title=f"{WF} ORC Exergy Analysis")
    plt.tight_layout()
    fig.savefig(f"{WF}_waterfall.svg")
    plt.close()

 