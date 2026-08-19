# -*- coding: utf-8 -*-
"""
reCreated after the HDD loss on Tue Mar  3 14:10:40 2026

@author: flori

Those functions aim to plot property diagrams using fluprodia library.

Get process list has to be made on the network code regarding its components to be stated on the plots

Optional: save function asks in the kernel if the plot as to be saved and in which formats.

Specific volume adapted for v0.9.16 ('vol' instead of 'v')

"""

"---Imports---"

from fluprodia import FluidPropertyDiagram as FPD
import matplotlib.pyplot as plt
import numpy as np

"---Get the plotting data for original network design---"

def get_processes(diagram, dictionary_plottingdata):
    """Internal method to centralized informations from network codes"""
    processes = {}
    # loop done by AI: allowing to state the tuple in any network code
    for label, data in dictionary_plottingdata.items():
        try:
            processes[label] = diagram.calc_individual_isoline(**data)
        except Exception as e:
            print(f"error detected on the component {label}: {e}")
   
    return processes 

"---Diagram functions---"
    
def plot_TS_diagram(working_fluid, dictionary_plottingdata):
    """"Plot property diagrams"""
    diagram = FPD(working_fluid)
    diagram.set_unit_system(T="°C", p="bar", h= 'kJ/kg')
 
    processes = get_processes(diagram, dictionary_plottingdata)
    
    # Automatic diagram bnd chooser
    all_s = []
    all_t = []
    for data in processes.values():
        all_s.extend(data["s"])
        all_t.extend(data["T"])
    
    # Margin = 10 %
    t_margin = (max(all_t) - min(all_t)) * 0.1
    s_margin = (max(all_s) - min(all_s)) * 0.1
    
    Tmin, Tmax = min(all_t) - t_margin, max(all_t) + t_margin
    Smin, Smax = min(all_s) - s_margin, max(all_s) + s_margin
    
    
    fig, ax = plt.subplots(1, figsize=(8,5))
    
    diagram.set_isolines_subcritical(0, Tmax)
    diagram.calc_isolines()
    diagram.draw_isolines(fig, ax, "Ts", Smin, Smax, Tmin, Tmax)
    
    for label, data in processes.items():
        ax.plot(data["s"], data["T"], label=label)
        ax.scatter(data["s"][0], data["T"][0], s= 40) # Me only the initial point with a personalized scale s, => (1/5 pts): ax.scatter(proc["s"][::5], proc["T"][::5], s=8) etc

    ax.legend(fontsize=12)
    ax.tick_params(axis='both', which='major', labelsize=12)
    plt.rcParams['axes.labelsize'] = 17
    plt.title("Diagram T-s", fontsize=15)
    plt.tight_layout()
    plt.show(block = False)

    return fig, "TS_diagram"

def plot_TH_diagram(working_fluid, dictionary_plottingdata):
    """"Plot property diagrams"""
    diagram = FPD(working_fluid)
    diagram.set_unit_system(T="°C", p="bar", h= 'kJ/kg')

    processes = get_processes(diagram, dictionary_plottingdata)
    
    # Automatic diagram bnd chooser
    all_h = []
    all_t = []
    for data in processes.values():
        all_h.extend(data["h"])
        all_t.extend(data["T"])
        
    # Margin = 10 %
    t_margin = (max(all_t) - min(all_t)) * 0.1
    h_margin = (max(all_h) - min(all_h)) * 0.1
    
    Tmin, Tmax = min(all_t) - t_margin, max(all_t) + t_margin
    Hmin, Hmax = min(all_h) - h_margin, max(all_h) + h_margin    
        
    fig, ax = plt.subplots(1, figsize=(8,5))
    
    diagram.set_isolines_subcritical(0, Tmax)
    diagram.calc_isolines()
    diagram.draw_isolines(fig, ax, "Th", Hmin, Hmax, Tmin, Tmax)
    
    for label, data in processes.items():
        ax.plot(data["h"], data["T"], label=label)
        ax.scatter(data["h"][0], data["T"][0], s= 40) # Me only the initial point with a personalized scale s, => (1/5 pts): ax.scatter(proc["s"][::5], proc["T"][::5], s=8) etc

    ax.legend(fontsize=12)
    ax.tick_params(axis='both', which='major', labelsize=12)
    plt.rcParams['axes.labelsize'] = 17
    plt.title("Diagram T-h", fontsize=15)
    plt.tight_layout()
    plt.show(block = False)

    return fig, "TH_diagram"

def plot_logPh_diagram(working_fluid, dictionary_plottingdata):
    """"Plot property diagrams"""
    diagram = FPD(working_fluid)
    diagram.set_unit_system(T="°C", p="bar", h = "kJ/kg")
  
    processes = get_processes(diagram, dictionary_plottingdata)

    fig1, ax1 = plt.subplots(1, figsize=(8,5))
    
    # Automatic diagram bnd chooser
    all_h = []
    all_p = []
    for data in processes.values():
        all_h.extend(data["h"])
        all_p.extend(data["p"])
    
    # Margin = 10 %
    h_margin = (max(all_h) - min(all_h)) * 0.1
    log_p_min, log_p_max = np.log10(min(all_p)), np.log10(max(all_p)) # ! log p
    p_log_margin = (log_p_max - log_p_min) * 0.1
    
    Hmin, Hmax = min(all_h) - h_margin, max(all_h) + h_margin
    Pmin, Pmax  = 10**(log_p_min - p_log_margin), 10**(log_p_max + p_log_margin)
    
    
    diagram.set_isolines_subcritical(0, Pmax)
    diagram.calc_isolines()
    diagram.draw_isolines(fig1, ax1, "logph", Hmin, Hmax, Pmin, Pmax)

    for label, data in processes.items():
        ax1.plot(data["h"], data["p"], label=label)
        ax1.scatter(data["h"][0], data["p"][0], s= 40) # Me only the initial point with a personalized scale s, => (1/5 pts): ax.scatter(proc["s"][::5], proc["T"][::5], s=8) etc

    ax1.legend(fontsize=12)
    ax1.tick_params(axis='both', which='major', labelsize=12)
    plt.rcParams['axes.labelsize'] = 17
    plt.title("Diagram logP-h", fontsize=15)
    plt.tight_layout()
    plt.show(block = False)

    return fig1, "PH_diagram"

def plot_Molier_diagram(working_fluid, dictionary_plottingdata):
    """"Plot property diagrams"""
    diagram = FPD(working_fluid)
    diagram.set_unit_system(T="°C", p="bar", h = "kJ/kg")
    
   
    processes = get_processes(diagram, dictionary_plottingdata)

    fig2, ax2 = plt.subplots(1, figsize=(8,5))
    
    # Automatic diagram bnd chooser using the distances between max and min
    all_h = []
    all_s = []
    for data in processes.values():
        all_h.extend(data["h"])
        all_s.extend(data["s"])
        
    # Margin = 10 %
    h_margin = (max(all_h) - min(all_h))*0.1
    s_margin = (max(all_s) - min(all_s))*0.1
    
    Hmin, Hmax = min(all_h) - h_margin, max(all_h) + h_margin
    Smin, Smax = min(all_s) - s_margin, max(all_s) + s_margin
    
    diagram.set_isolines_subcritical(0, Hmax)
    diagram.calc_isolines()
    diagram.draw_isolines(fig2, ax2, "hs", Smin, Smax, Hmin, Hmax)

    for label, data in processes.items():
        ax2.plot(data["s"], data["h"], label=label)
        ax2.scatter(data["s"][0], data["h"][0], s= 40) # Me only the initial point with a personalized scale s, => (1/5 pts): ax.scatter(proc["s"][::5], proc["T"][::5], s=8) etc

    ax2.legend(fontsize=12)
    ax2.tick_params(axis='both', which='major', labelsize=12)
    plt.rcParams['axes.labelsize'] = 17
    plt.title("Molier diagram h-s", fontsize=15)
    plt.tight_layout()
    plt.show(block = False)

    return fig2, "Molier_diagram"

def plot_Clapeyron_diagram(working_fluid, dictionary_plottingdata):
    """"Plot property diagrams"""
    diagram = FPD(working_fluid)
    diagram.set_unit_system(T="°C", p="bar", h = "kJ/kg")
    
    processes = get_processes(diagram, dictionary_plottingdata)

    fig3, ax3 = plt.subplots(1, figsize=(8,5))
    
    all_v = []
    all_p = []
    for data in processes.values():
        all_v.extend(data["vol"])
        all_p.extend(data["p"])

    # Margin = 10 %
    log_v_min, log_v_max = np.log10(min(all_v)), np.log10(max(all_v))
    v_log_margin = (log_v_max - log_v_min) * 0.1
    p_margin = (max(all_p) - min(all_p)) * 0.1
    
    Vmin, Vmax = 10**(log_v_min - v_log_margin), 10**(log_v_max + v_log_margin)
    Pmin, Pmax = min(all_p) - p_margin, max(all_p) + p_margin
    
    diagram.set_isolines_subcritical(0, Pmax)
    diagram.calc_isolines()
    diagram.draw_isolines(fig3, ax3, "plogv", Vmin, Vmax, Pmin, Pmax)

    for label, data in processes.items():
        ax3.plot(data["vol"], data["p"], label=label)
        ax3.scatter(data["vol"][0], data["p"][0], s= 40) # Me only the initial point with a personalized scale s, => (1/5 pts): ax.scatter(proc["s"][::5], proc["T"][::5], s=8) etc

    ax3.legend(fontsize=12)
    ax3.tick_params(axis='both', which='major', labelsize=12)
    plt.rcParams['axes.labelsize'] = 17
    plt.title("Clapeyron diagram p-logv", fontsize=15)
    plt.tight_layout()
    plt.show(block = False)

    return fig3, "Clapeyron_diagram"

"---Optional: command to ask in the spyder kernel if the user want to save, which diagrams, & at which format---"

def save_plots(figures):
    """Interactive prompt to save figures"""
    save = input("Do you wish to save somme plots ? (Yes / No) : ").strip().lower()
    if save not in ["oui", "o", "yes", "y","Yes", "YES"]:
        return
    
    print("\nAvailable diagrams :")
    for i, name in enumerate(figures.keys(), 1):
        print(f"  {i} - {name}")
        
    choice = input("\nnb (ex: 1 3) or 'all' : ").strip().lower()
        
    if choice == "all":
        selected = list(figures.keys())
    else:
        idx = [int(i) - 1 for i in choice.split()]
        selected = [list(figures.keys())[i] for i in idx]
            
    fmt = input("Format ? (svg / png) : ").strip().lower()

    if fmt not in ["svg", "png"]:
        print("Not recognized format → operation canceled.")
    for name in selected:
        fig = figures[name]
        fig.canvas.draw() # Force the svg cash to be reloaded (white svg problem resolved!)
        fig.savefig(f"{name}.{fmt}", dpi=300, bbox_inches="tight")
        print(f"Sauvegardé : {name}.{fmt}")
