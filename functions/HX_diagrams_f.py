# -*- coding: utf-8 -*-
"""
reCreated after the HDD data loss on Mon Mar  2 11:34:19 2026

@author: flori

This file contains fcts to plot QT diagrams in different type of TESPy heat exchangers.

HeatExchanger, Condenser or SimpleHeatExchangers have to be done by hand.

MovingBoundaryHeatExchanger & SectionedHeatExchanger have a special command to harvest the data.

WARNING!!! the units to be putted in the networks are temperature = 'degC', pressure = 'bar', enthalpy 
= 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW'. If you want to use other units beware to adapt this code aswell.

"""

from matplotlib import pyplot as plt

"Functions created for counter flow HXs (with hot output/ cold input at 0 kW)"

def plot_tq_MBHX_SHX(component, label):
    """
    Plots the Temperature (T) over Heat Flow (Q) for a TESPy component.
    
    Parameters:
    - component: The TESPy SectionedHeatExchanger/MovingBoundaryHeatExchanger only
    - label: String name for the plot title 
    """
    # Extract plotting data 
    heat, T_hot, T_cold, heat_per_section, td_log_per_section = component.calc_sections()
    
    # Warning W because calc.sections() is an embedded TESPy fct /1e3 => kW for version previous to v0.9.16
    heat = heat

    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Warning Kelvin because calc.sections()  is an embedded TESPy fct T -273.15 => °C for version previous to v0.9.16
    ax.plot(heat, T_hot, "o-", color="red", label="Hot Side")
    ax.plot(heat, T_cold, "o-", color="blue", label="Cold Side")
    ax.set_title(f"T-Q Diagram: {label}", fontsize=18)
    ax.set_ylabel("Temperature in °C", fontsize=18)
    ax.set_xlabel("Cumulative Heat Transferred in kW", fontsize=18)
    
    ax.legend(fontsize=16)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()
    
    # Save as SVG with the inputed label as name
    filename = f"{label.strip().replace(' ', '_')}.svg"
    plt.savefig(filename, format='svg', bbox_inches='tight')
    
    plt.show()
    
def plot_tq_HX(component, label):
    """
    Plots the Temperature (T) over Heat Flow (Q) for a TESPy component.
    
    Parameters:
    - component: The TESPy Heatexchanger type only
    - label: String name for the plot title 
    """
    # Extract plotting data 
    Q_total = abs(component.Q.val)
        
    # Hot side: in1 -> out1
    T_hot_in = component.inl[0].T.val
    T_hot_out = component.outl[0].T.val
    
    # Cold side: in2 -> out2
    T_cold_in = component.inl[1].T.val
    T_cold_out = component.outl[1].T.val
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # X-axis: 0 to Total Heat
    heat = [0, Q_total]
    # For counter-flow: Hot enters at Q_total, Cold enters at 0
    ax.plot(heat , [T_hot_out, T_hot_in], "o-", color="red", label="Hot Side")
    ax.plot(heat , [T_cold_in, T_cold_out], "o-", color="blue", label="Cold Side")

    ax.set_title(f"T-Q Diagram: {label}", fontsize=18)
    ax.set_ylabel("Temperature in °C", fontsize=18)
    ax.set_xlabel("Cumulative Heat Transferred in kW", fontsize=18)
    
    ax.legend(fontsize=16)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()
    
    # Save as SVG with the inputed label as name
    filename = f"{label.strip().replace(' ', '_')}.svg"
    plt.savefig(filename, format='svg', bbox_inches='tight')
    
    plt.show()

def plot_tq_CD(component, label):
    """
    Plots the Temperature (T) over Heat Flow (Q) for a TESPy component.
    
    Parameters:
    - component: The TESPy Condenser only HX like but We have to take the saturation T (dew point) by hand
    - label: String name for the plot title 
    """
    
    # Extract plotting data 
    Q_total = abs(component.Q.val)
    m_hot = component.inl[0].m.val
    p_hot = component.inl[0].p.val
    fluid_hot = component.inl[0].fluid.val
    
    # Hot side: in1 -> out1
    T_hot_in = component.inl[0].T.val
    T_hot_out = component.outl[0].T.val
    
    # Cold side: in2 -> out2
    T_cold_in = component.inl[1].T.val
    T_cold_out = component.outl[1].T.val

    # Dew point determination
    # Enthalpy & pressure at x = 1 ? 
    h_hot_in = component.inl[0].h.val
    
    from CoolProp.CoolProp import PropsSI

    # Fluid name recuparation
    fluid_name = list(fluid_hot.keys())[0]
    
    # Conversion of Pa to bar
    p_hot_Pa = p_hot * 1e5  
    
    h_sat_v = PropsSI("H", "P", p_hot_Pa, "Q", 1, fluid_name)  / 1e3  # (J/kg to kJ/kg)
    T_sat_v = PropsSI("T", "P", p_hot_Pa, "Q", 1, fluid_name) - 273.15 # K to °C
    
    # Q desuperheating calculation Q_desuperheating = m * (h_in - h_sat)
    Q_desuperheating = (m_hot * (h_hot_in - h_sat_v))
    
    # Dew point location at (Q_total - Q_desuperheating) on x axis
    Q_dew_point =  abs(Q_total - Q_desuperheating)
    
    print(f"--- Condenser: {label} ---")
    print(f"Q_desuperheating: {Q_desuperheating:.2f} kW", f"Q_total: {Q_total:.2f} kW")
    print(f"Heat flow at Dew Point: {Q_dew_point:.2f} kW")
    print(f"Temperature at Dew Point: {T_sat_v:.2f} °C\n")


    fig, ax = plt.subplots(figsize=(10, 6))

    # Hot side: hot input at Q_total, dew point, hot output at 0 kW
    ax.plot([0, Q_dew_point, Q_total], [T_hot_out, T_sat_v, T_hot_in], 
            "o-", color="red", label="Hot Side")
    
    # Cold side: cold output at Q_total, cold input at 0 kW
    ax.plot([0, Q_total], [T_cold_in, T_cold_out], 
            "o-", color="blue", label="Cold Side")

    ax.set_title(f"T-Q Diagram: {label}", fontsize=18)
    ax.set_ylabel("Temperature in °C", fontsize=18)
    ax.set_xlabel("Cumulative Heat Transferred in kW", fontsize=18)
    ax.legend(fontsize=16)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()

    # Save in SVG
    filename = f"{label.strip().replace(' ', '_')}.svg"
    plt.savefig(filename, format='svg', bbox_inches='tight')
    
    plt.show()

    





