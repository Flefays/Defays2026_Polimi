# -*- coding: utf-8 -*-
"""
Created on Thu Jul 23 17:10:20 2026

@author: flori

Exergy Balance using ModelTemplate

Integrates Exerpy (auto-imported as part of the new feature set) and pandas.

The script includes a Sankey diagram generation using Plotly.
Refactored from a legacy script originally based on matplotlib/pyplot documentation.

"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go

from _02_heat_pump import HeatPumpModel

T_amb = 10 
p_amb = 1.013  

for WF in ["R134a"]: # Allow to do the calculation for multiple working fluid

    hp = HeatPumpModel(WF, Tamb=T_amb, pamb=p_amb)
    hp.nw.print_results()
    print(f"\nCOP = {hp.get_parameter('COP'):.3f}")
    print(f"T_evap = {hp.get_parameter('T_evap'):.2f} degC")
    print(f"T_cond = {hp.get_parameter('T_cond'):.2f} degC")
    hp.save_design()
    
    fuel = {"inputs": ['e0','E1'], "outputs": ['E2']}
    product = {"inputs": ['E3'], "outputs": ['E4']}

    exergy_kwargs = {"Tamb": T_amb, "pamb": p_amb, "E_F": fuel, "E_P": product}
    run_exergy = lambda model: model.run_exergy_analysis(**exergy_kwargs)

    ean = hp.run_exergy_analysis(**exergy_kwargs)
    print(f"\n{'='*60}")
    print(f"{'EXERGY ANALYSIS':^60}")
    print(f"{'='*60}")
    
    # Get DataFrames directly from Exerpy
    df_comp, df_material, df_power = ean.exergy_results()

    # --- Embedded WATERFALL PLOT ---
    fig, ax = ean.plot_exergy_waterfall(title=f"{WF} Heat Pump Exergy Analysis")
    plt.tight_layout()
    fig.savefig(f"{WF}_waterfall.svg")
    plt.close()
    
    #%% --- SANKEY DIAGRAM ---
    # Convert index to 'Component' column if needed (Exerpy often uses index for component names)
    if "Component" not in df_comp.columns:
        df_sankey = df_comp.reset_index().rename(columns={"index": "Component", "name": "Component"})
    else:
        df_sankey = df_comp.copy()

    # Exclude 'TOT' row to focus on individual components
    df_sankey = df_sankey[df_sankey["Component"] != "TOT"]

    # Define Nodes
    components = df_sankey["Component"].tolist()
    nodes = ["Fuel Source"] + components + ["Product Output", "Exergy Destruction", "Exergy Loss"]
    node_indices = {name: i for i, name in enumerate(nodes)}

    # Build Links with Balanced Logic
    sources = []
    targets = []
    values = []

    for _, row in df_sankey.iterrows():
        comp = row["Component"]
        
        # Safely extract values (handles both "E_F [kW]" and "E_F" just in case)
        e_f = row.get("E_F [kW]", row.get("E_F", 0))
        e_p = row.get("E_P [kW]", row.get("E_P", 0))
        e_d = row.get("E_D [kW]", row.get("E_D", 0))
        e_l_val = row.get("E_L [kW]", row.get("E_L", 0))
        
        # Handle the Condenser sign convention: 
        # In exergy, if E_F and E_P are negative, |E_P| is often the input (fuel)
        # and |E_F| is the output (product).
        if e_f < 0:
            f_in, p_out = abs(e_p), abs(e_f)
        else:
            f_in, p_out = e_f, e_p
            
        e_l = abs(e_l_val)

        # Fuel Source -> Component
        if f_in > 0:
            sources.append(node_indices["Fuel Source"])
            targets.append(node_indices[comp])
            values.append(f_in)

        # Component -> Product Output
        if p_out > 0:
            sources.append(node_indices[comp])
            targets.append(node_indices["Product Output"])
            values.append(p_out)

        # Component -> Exergy Destruction
        if e_d > 0:
            sources.append(node_indices[comp])
            targets.append(node_indices["Exergy Destruction"])
            values.append(e_d)
            
        # Component -> Exergy Loss
        if e_l > 0:
            sources.append(node_indices[comp])
            targets.append(node_indices["Exergy Loss"])
            values.append(e_l)

    # Create and Save Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=nodes),
        link=dict(source=sources, target=targets, value=values)
    )])

    fig.update_layout(title_text=f"Exergy Sankey Diagram - {WF}", font_size=12)

    # Save to HTML dynamically based on the working fluid
    html_filename = f"{WF}_sankey_diagram.html"
    fig.write_html(html_filename)
    print(f"Saved Sankey diagram to: {html_filename}")
    
    """
    This svg do not seems to be practical for LaTeX,
    maybe a pdf or png is more suitable
    """
    # Save vector SVG for LaTeX
    # install kaleido !
    png_filename = f"{WF}_sankey_diagram.png"
    fig.write_image(png_filename)
    print(f"Saved Sankey diagram to: {png_filename}")