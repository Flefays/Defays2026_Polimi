# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 14:38:01 2026

@author: flori

The result W_net is different than in the exercise because the DHP pump and the cooling water pump are given as a cte

"""

from CoolProp.CoolProp import PropsSI as PSI
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

"(1st step)"

m_w1 = 500/3.6 #kg/s

# w0
T_w0 = 160 # °C
x_w0 = 0 
m_w0 = m_w1

p_w0 = PSI('P','Q', x_w0, 'T', T_w0 +273.15, 'water')/1e5 # Pa
h_w0 = PSI('H','Q', x_w0, 'T', T_w0 +273.15, 'water')/1e3 # kJ/kg
s_w0 = PSI('S','Q', x_w0, 'T', T_w0 +273.15, 'water') # J/kgK

# w1
p_w1 = p_w0 # no pressure drop

# w2
p_w2 = p_w0 # no pressure drop

# c5-c0
p_c5 = 12 # bar
x_c5 = 1

T_c5 = PSI('T','Q', x_c5 , 'P', p_c5*1e5, 'Isopentane')-273.15 # °C
h_c5  = PSI('H','Q', x_c5 , 'P', p_c5*1e5, 'Isopentane')/1e3 # kJ/kg
s_c5  = PSI('S','Q', x_c5 , 'P', p_c5*1e5, 'Isopentane') # J/kgK

# c4
x_c4 = 0

p_c4 = p_c5 # no pressure drop
T_c4 = PSI('T','Q', x_c4 , 'P', p_c4*1e5, 'Isopentane')-273.15 # °C
h_c4 = PSI('H','Q', x_c4 , 'P', p_c4*1e5, 'Isopentane')/1e3 # kJ/kg
s_c4 = PSI('S','Q', x_c4 , 'P', p_c4*1e5, 'Isopentane') # J/kgK

# c3
p_c3 = p_c5 # no pressure drop

# c2
T_c2 = 30 # 30°C
x_c2 = 0

p_c2 = PSI('P','Q', x_c2, 'T', T_c2 +273.15, 'Isopentane')/1e5 # Pa
h_c2 = PSI('H','Q', x_c2, 'T', T_c2 +273.15, 'Isopentane')/1e3 # kJ/kg
s_c2 = PSI('S','Q', x_c2, 'T', T_c2 +273.15, 'Isopentane') # J/kgK

# c1
p_c1 = p_c2 # no pressure drop

# Turbine
eff_s = 0.8
S = s_c5 

h_c1_s = PSI('H','S', S , 'P', p_c1*1e5, 'Isopentane')/1e3 # kJ/kg

# a0
T_a0 = 18 #°C

# a1
T_a1 = T_a0 + 8 

"(2nd step)"

# c1
h_c1 = (eff_s*(h_c1_s-h_c5)) + h_c5

T_c1 = PSI('T','H', h_c1*1e3 , 'P', p_c1*1e5, 'Isopentane')-273.15 # °C
s_c1 = PSI('S','H', h_c1*1e3, 'P', p_c1*1e5, 'Isopentane') # J/kgK

# w1
T_w1 = T_c4 + 5 # evaporator pinch point ttd_l in tespy

h_w1 = PSI('H','P', p_w1*1e5, 'T', T_w1 +273.15, 'water')/1e3 # kJ/kg
x_w1 = PSI('Q','P', p_w1*1e5, 'H', h_w1*1e3, 'water') # [-]
s_w1 = PSI('S','P', p_w1*1e5, 'H', h_w1*1e3, 'water') # J/kgK

# Evaporator
Q_evap = m_w1* (h_w0 -h_w1)
m_r = Q_evap/(h_c5-h_c4)

# NEED to fix the pump eff_s and p or x at cooling water side or m ?

'(3rd step)'

# a0
p_a0 = 3 #bar

h_a0 = PSI('H','P', p_a0*1e5, 'T', T_a0 +273.15, 'water')/1e3 # kJ/kg
x_a0 = PSI('Q','P', p_a0*1e5, 'H', h_a0*1e3, 'water') # [-]
s_a0 = PSI('S','P', p_a0*1e5, 'H', h_a0*1e3, 'water') # J/kgK

# a1
p_a1 = p_a0 - 2 #2 bar pressure drop in the condenser

h_a1 = PSI('H','P', p_a1*1e5, 'T', T_a1 +273.15, 'water')/1e3 # kJ/kg
x_a1 = PSI('Q','P', p_a1*1e5, 'H', h_a1*1e3, 'water') # [-]
s_a1 = PSI('S','P', p_a1*1e5, 'H', h_a1*1e3, 'water') # J/kgK

# condenser
Q_cd = m_r*(h_c1 -h_c2)
m_w2 = Q_cd/(h_a1 - h_a0)


"""
# pump
eff_p_s = 0.6
S = s_c2

h_c3_s = PSI('H','S', S , 'P', p_c3*1e5, 'Isopentane')/1e3 # kJ/kg

# c3
h_c3 = ((h_c3_s - h_c2)/eff_p_s) + h_c2
T_c3 = PSI('T', 'H', h_c3*1e3, 'P', p_c3*1e5, 'Isopentane') - 273.15 # °C
"""

"--- New version using eta hydraulic---"

eff_p = 0.7

# specific volume ?
rho_c2 = PSI('D', 'T', T_c2 + 273.15, 'Q', x_c2, 'Isopentane') # kg/m3
v_in = 1 / rho_c2 # specific volume in m3/kg

# work ?
delta_p = (p_c3 - p_c2) * 1e5 
work_hyd = (v_in * delta_p) / 1e3 # Convert J/kg to kJ/kg

# hydraulic efficiency: h_actual = h_in + (V * deltaP) / eff_hyd
h_c3 = h_c2 + (work_hyd / eff_p)

T_c3 = PSI('T', 'H', h_c3 * 1e3, 'P', p_c3 * 1e5, 'Isopentane') - 273.15  # °C

"---end---"


# eco
Q_eco = m_r * (h_c4 - h_c3)

# w2
h_w2 = -(Q_eco/m_w1) + h_w1

T_w2 = PSI('T', 'H', h_w2*1e3, 'P', p_w2*1e5, 'water')-273.15 #°C
x_w2 = PSI('Q','P', p_w2*1e5, 'H', h_w2*1e3, 'water') # [-]
s_w2 = PSI('S','P', p_w2*1e5, 'H', h_w2*1e3, 'water') # J/kgK

# c0
p_c0 = p_c5
T_c0 = T_c5
h_c0 = h_c5


'print'

points = ['w0', 'w1', 'w2','c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'a0', 'a1']
pressions = [p_w0, p_w1, p_w2, p_c0, p_c1, p_c2, p_c3, p_c4, p_c5, p_a0, p_a1]
enthalpies = [h_w0, h_w1, h_w2, h_c0, h_c1, h_c2, h_c3, h_c4, h_c5, h_a0, h_a1]
temperatures = [T_w0, T_w1, T_w2, T_c0, T_c1, T_c2, T_c3, T_c4, T_c5, T_a0, T_a1]
flowrates = [m_w1, m_w1, m_w1, m_r, m_r, m_r, m_r, m_r, m_r, m_w2, m_w2]

print(f"\n{'Point':<5} | {'Pressure (bar)':<15} | {'Enthalpy (kJ/kg)':<18} | {'Temperature (°C)':<15}| {'Flowrates (kg/s)':<15}")
print("-" * 62)
for pt, p, h, t, m in zip(points, pressions, enthalpies, temperatures, flowrates):
    print(f"{pt:<5} | {p:<15.4f} | {h:<18.4f} | {t:<15.4f}| {m:<15.4f}")

print("\n" + "="*62 + "\n")

#--- Optimisation of p_c5 (the evaporator saturation pressure) ---

"""
This step used AI since its straitghforward from this simple hard coded cycle to do a loop

AI allowed to not rewrite all lines. 
"""

# --- Fixed Parameters ---
m_w1 = 500 / 3.6  # kg/s (Heat source flow rate)
T_w0 = 160        # °C
x_w0 = 0          # Saturated liquid
eff_s_turb = 0.8  # Turbine isentropic efficiency
eff_p = 0.7       # Pump efficiency
T_c2_set = 30     # °C (Condensation temperature)

# Evaporation pressure range 
p_evap_range = np.linspace(4, 12, 20) 

results = []

for p_c5 in p_evap_range:
    try:
        # 1. Heat Source (Water)
        p_w0 = PSI('P', 'Q', x_w0, 'T', T_w0 + 273.15, 'water') / 1e5
        h_w0 = PSI('H', 'Q', x_w0, 'T', T_w0 + 273.15, 'water') / 1e3
        
        # 2. Saturated Vapor State (c5)
        x_c5 = 1
        h_c5 = PSI('H', 'Q', x_c5, 'P', p_c5 * 1e5, 'Isopentane') / 1e3
        s_c5 = PSI('S', 'Q', x_c5, 'P', p_c5 * 1e5, 'Isopentane')
        
        # 3. Saturated Liquid State (c4)
        x_c4 = 0
        h_c4 = PSI('H', 'Q', x_c4, 'P', p_c5 * 1e5, 'Isopentane') / 1e3
        T_c4 = PSI('T', 'Q', x_c4, 'P', p_c5 * 1e5, 'Isopentane') - 273.15
        
        # 4. Condenser (c2)
        p_c2 = PSI('P', 'Q', 0, 'T', T_c2_set + 273.15, 'Isopentane') / 1e5
        h_c2 = PSI('H', 'Q', 0, 'T', T_c2_set + 273.15, 'Isopentane') / 1e3
        
        # 5. Turbine (Expansion c5 -> c1)
        h_c1_s = PSI('H', 'S', s_c5, 'P', p_c2 * 1e5, 'Isopentane') / 1e3
        dh_turb = h_c5 - h_c1_s # Isentropic enthalpy drop
        h_c1 = h_c5 - (eff_s_turb * (h_c5 - h_c1_s))
        w_turb_spec = h_c5 - h_c1 # kJ/kg
        
        # 6. Evaporator Pinch Point (Calculating mass flow rate m_r)
        T_w1 = T_c4 + 5 # Pinch point
        h_w1 = PSI('H', 'P', p_w0 * 1e5, 'T', T_w1 + 273.15, 'water') / 1e3
        Q_evap_upper = m_w1 * (h_w0 - h_w1)
        m_r = Q_evap_upper / (h_c5 - h_c4)
        
        # 7. Pump (c2 -> c3)
        rho_c2 = PSI('D', 'T', T_c2_set + 273.15, 'Q', 0, 'Isopentane')
        work_p_spec = ((p_c5 - p_c2) * 1e5 / rho_c2) / 1e3 / eff_p # kJ/kg
        
        # 8. Power Balance
        W_turb = m_r * w_turb_spec
        W_pump = m_r * work_p_spec
        W_DHP = 550 #kW
        W_pump_cw = 238.012 #kW
        W_ancillaries = W_DHP + W_pump_cw
        W_net = W_turb - W_pump - W_ancillaries
        
        # E. ECONOMIZER & WATER EXIT (T_w2)
        # Heat required to preheat Isopentane from c3 to c4
        Q_eco = m_r * (h_c4 - h_c3)
        # Enthalpy of water leaving the economizer
        h_w2 = h_w1 - (Q_eco / m_w1)
        p_w2 = p_w0
        # Final temperature of water source
        T_w2 = PSI('T', 'H', h_w2 * 1e3, 'P', p_w2*1e5, 'water') - 273.15
        
        results.append({
            'Peva': p_c5,
            'm_ORC': m_r,
            'Dh_turb': w_turb_spec,
            'W_net': W_net,
            'T_w2': T_w2
        })
    except:
        continue

df = pd.DataFrame(results)

# --- Plotting Results (AI used to do the plot code faster)---

# Global settings 
plt.rcParams.update({
    'font.size': 12,          # Base font size
    'axes.titlesize': 16,     # Title of the subplots
    'axes.labelsize': 15,     # x and y labels
    'xtick.labelsize': 12,    # x-axis tick labels
    'ytick.labelsize': 12,    # y-axis tick labels
    'legend.fontsize': 12,    # Legend font size
    'figure.titlesize': 18    # Overall figure title
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Net Power Output
ax1.plot(df['Peva'], df['W_net'], color='tab:orange', linewidth=2)
ax1.set_title('Net Power Output')
ax1.set_xlabel('Evaporation pressure [bar]')
ax1.set_ylabel('Net power output [kW]')
ax1.grid(True, linestyle='--', alpha=0.7)
# Set scale 
ax1.set_ylim(4000, 6000) 
ax1.set_xlim(0, 14) 

# Plot 2: Flow Rate and Enthalpy Drop
ax2_twin = ax2.twinx()
lns1 = ax2.plot(df['Peva'], df['m_ORC'], color='tab:orange', label='m,ORC')
lns2 = ax2_twin.plot(df['Peva'], df['Dh_turb'], color='tab:blue', label='Dh,turb')

ax2.set_title('Flow rate and Enthalpy drop')
ax2.set_xlabel('Evaporation pressure [bar]')
ax2.set_ylabel('ORC mass flow rate [kg/s]')
ax2_twin.set_ylabel('Turbine enthalpy drop [kJ/kg]')
# Set scale 
ax2.set_ylim(0, 200)
ax2_twin.set_ylim(0, 100)
ax2.set_xlim(0,14)

# Combined legend
lns = lns1 + lns2
labs = [l.get_label() for l in lns]
ax2.legend(lns, labs, loc='center right')
ax2.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('Optimization.svg', format='svg', bbox_inches='tight')
plt.show()

# Plot 3: Water Exit Temperature (T_w2)

fig, (ax3) = plt.subplots(figsize=(12, 5))

ax3.plot(df['Peva'], df['T_w2'], color='tab:green', linewidth=2)
ax3.set_title('Water Exit Temperature ($T_{w2}$)')
ax3.set_xlabel('Evaporation pressure [bar]')
ax3.set_ylabel('Temperature [°C]')
ax3.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
fig.savefig('water_exit_temperature.svg', format='svg', bbox_inches='tight')
plt.show()

# Displaying data table preview
print(df.head(10).T)



# --- Identifying the Optimum ---
# Find the index of the maximum net power
idx_max = df['W_net'].idxmax()

# Extract the corresponding optimal values
p_opt = df.loc[idx_max, 'Peva']
w_max = df.loc[idx_max, 'W_net']
m_opt = df.loc[idx_max, 'm_ORC']
dh_opt = df.loc[idx_max, 'Dh_turb']

print("\n" + "="*40)
print(f"{'OPTIMIZATION RESULTS':^40}")
print("="*40)
print(f"{'Optimal Evap. Pressure:':<25} {p_opt:>8.3f} bar")
print(f"{'Maximal Net Power:':<25} {w_max:>8.2f} kW")
print(f"{'ORC Mass Flow Rate:':<25} {m_opt:>8.2f} kg/s")
print(f"{'Turbine Enthalpy Drop:':<25} {dh_opt:>8.2f} kJ/kg")
print("="*40)





