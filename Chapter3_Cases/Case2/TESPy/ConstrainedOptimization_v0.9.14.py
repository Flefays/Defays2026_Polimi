# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 17:57:58 2026

@author: Florian Defays, (Politecnico di Milano)

Optimisation of a geothermal ORC with a minimal geofluid temperature reinjection of 70°C.

Using v0.9.14

"""

"---Standard Imports---"

import numpy as np
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI as PSI

# Package to Handle Dataframes (csv)
import pandas as pd

# Pymoo Optimizer, Newton Raphson
from pymoo.optimize import minimize
from tespy.tools.optimization import OptimizationProblem
from pymoo.algorithms.soo.nonconvex.nrbo import NRBO 

"---Function Imports---"

# Path (Have to be complete if the file locations are not linked) 
import sys
sys.path.append(r'D:\codes\functions')

# Personalized imports for diagrams
from Fluprodia_diagrams_f import plot_TS_diagram, plot_TH_diagram, plot_Clapeyron_diagram, plot_Molier_diagram, plot_logPh_diagram, save_plots
from HX_diagrams_f import plot_tq_MBHX_SHX, plot_tq_HX

"---TESPy related imports"

# Import the network object
from tespy.networks import Network

# Import the fluid and power, both for components and connections 
from tespy.components import Source, Sink, CycleCloser, Pump, Turbine, MovingBoundaryHeatExchanger, HeatExchanger
from tespy.components import PowerBus, PowerSink, Motor, Generator
from tespy.connections import Connection, PowerConnection

"---ORC model---"

class Geo_ORC():
    """Class template for TESPy model usage in other modules like the optimisation module."""
    def __init__(self, working_f):
        self.working_f = working_f
        self._create_network()

    def _create_network(self):
        
        "---Network definition---"

        # Definition + disable/enable iteration informations
        self.nw = Network(iterinfo = False)

        # Change the default units
        self.nw.units.set_defaults(temperature = 'degC', pressure = 'bar', enthalpy = 'kJ/kg', entropy = 'J/kgK', power = 'kW', heat = 'kW')
        
        "---Fluid Components---"
        
        # Geo Cycle
        w1_su = Source('pumped water')
        w1_ex = Sink('injected water')
        
        # Main Cycle
        cc = CycleCloser('cyclecloser')
        turb = Turbine('turbine')
        cond = MovingBoundaryHeatExchanger('condenser')
        pp = Pump('pump')
        eco = HeatExchanger('economizer')
        evap = HeatExchanger('evaporator')
        
        # Cooling Cycle
        w2_su = Source('cooling water source')
        w2_ex = Sink('cooling water sink')
        
        "---Fluid Connections---"
        
        # Geo Cycle
        w0 = Connection(w1_su, 'out1', evap, 'in1', label= 'w0')
        w1 = Connection(evap, 'out1', eco, 'in1', label= 'w1')
        w2 = Connection(eco, 'out1', w1_ex, 'in1', label= 'w2')
        
        self.nw.add_conns(w0, w1, w2)
        
        # Main Cycle
        c0 = Connection(cc, 'out1', turb, 'in1', label= 'c0')
        c1 = Connection(turb, 'out1', cond, 'in1', label= 'c1')
        c2 = Connection(cond, 'out1', pp, 'in1', label= 'c2')
        c3 = Connection(pp, 'out1', eco, 'in2', label= 'c3')
        c4 = Connection(eco, 'out2', evap, 'in2', label= 'c4')
        c5 = Connection(evap, 'out2', cc, 'in1', label= 'c5')
        
        self.nw.add_conns(c0, c1, c2, c3, c4, c5)
        
        # Cooling Cycle
        a0 = Connection(w2_su, 'out1', cond, 'in2', label= 'a0')
        a1 = Connection(cond, 'out2', w2_ex, 'in1', label= 'a1')

        self.nw.add_conns(a0, a1)
        
        "---Electric Components---"
        
        # Energy Balance Between the turbine, the pump and the grid
        ORC_bus = PowerBus('electricity bus of the ORC', num_in = 1, num_out = 2)
        
        # Grid, motor and generator Components
        ORC_grid = PowerSink('grid connection')
        motor = Motor('motor')
        generator = Generator('alternator')
        
        "---Electric Connections---"
        
        e0 = PowerConnection(turb, 'power', generator, 'power_in', label='e0')
        e1 = PowerConnection(generator, 'power_out', ORC_bus, 'power_in1', label='e1')
        e2 = PowerConnection(ORC_bus, 'power_out1', motor, 'power_in', label='e2')
        e3 = PowerConnection(motor, 'power_out', pp, 'power', label='e3')
        e4 = PowerConnection(ORC_bus, 'power_out2', ORC_grid, 'power', label='e4') # Net ORC's power output
       
        self.nw.add_conns(e0, e1, e2, e3, e4)
        
        "---Parametrisation---"
        
        # water definition
        w_f = {'water': 1}  # {'fluid': massic fraction}
        
        # Geo Cycle
        T_sat_ORC = PSI('T', 'Q', 0, 'P', 12e5, self.working_f) - 273.15  # = T_c4 allowing to help the solver with the 0D evaporator pinch ttd_l (resolved in v0.9.16)
        w0.set_attr(fluid = w_f, m = 500/3.6, x = 0, T = 160); w1.set_attr(T = T_sat_ORC +5); w2.set_attr() 
        
        # Main Cycle
        c0.set_attr(); c1.set_attr(); c2.set_attr(fluid = {self.working_f:1}, T = 30, x = 0)
        c3.set_attr(); c4.set_attr(x = 0); c5.set_attr(x = 1, p = 12)
        
        # Cooling Cycle
        a0.set_attr(fluid = w_f, T = 18, p=3); a1.set_attr(T = 18 + 8) # x=0 or a Pressure
       
        # Components
        eco.set_attr(pr1 = 1, pr2 = 1)
        evap.set_attr(pr1 = 1, pr2 = 1) 
        cond.set_attr(pr1 = 1, dp2 = 2) 
        turb.set_attr(eta_s = 0.8)
        pp.set_attr( eta = 0.7) 
        
        # Power
        generator.set_attr(eta = 1)
        motor.set_attr(eta = 1) 
        
        self.nw.solve('design')
        
        # changing for the pinch
        w1.set_attr(T = None)
        evap.set_attr(ttd_l = 5 )     
        
        self.nw.solve('design')
        self.nw.print_results()
        
        # QT diagrams
        plot_tq_HX(eco, 'Economizer')
        plot_tq_HX(evap, 'Evaporator')
        plot_tq_MBHX_SHX(cond, 'Condenser')
        
        "---Power & Efficiency of the previous parametrization---"

        Net_Power = e4.E.val-550-238 # Net ORC's power - assumed constant powers from the ancilaries
        Net_Heat  = abs(eco.Q.val + evap.Q.val)
        Th_eff    = (Net_Power/Net_Heat)*100

        print(f"Net Power  : {Net_Power:.2f} kW", f"Net Heat   : {Net_Heat:.2f} kW", f"Efficacité : {Th_eff:.2f} %")
       
        self._LB = '_LB.json'
        self.nw.save(self._LB)
        self._solved = True
        
    def property_diagrams(self, working_f):
        """extraction of data and call to plot functions"""
        
        # Build the data dictionary
        dico = {
            
            "Turbine": self.nw.get_comp('turbine').get_plotting_data()[1],
            "Condenser": self.nw.get_comp('condenser').get_plotting_data()[1],
            "Pump": self.nw.get_comp('pump').get_plotting_data()[1],
            "Preheater": self.nw.get_comp('economizer').get_plotting_data()[2],
            "Evaporator": self.nw.get_comp('evaporator').get_plotting_data()[2],
        }

        # Cal of plotting functions
        figures = {}
        fig, name = plot_TS_diagram(working_f, dico)
        figures[name] = fig
        fig, name = plot_TH_diagram(working_f, dico)
        figures[name] = fig
        fig, name = plot_Clapeyron_diagram(working_f, dico)
        figures[name] = fig
        fig, name = plot_Molier_diagram(working_f, dico)
        figures[name] = fig
        fig, name = plot_logPh_diagram(working_f, dico)
        figures[name] = fig

        # Plot saves
        save_plots(figures)
        return fig       
        
    "---Functions from TESPy source code documentation about optimisation---"
        
    def get_param(self, obj, label, parameter):
        """Get thevalue of a parameter in the network"s unit system.

        Parameters
        ----------
        obj : str
            Object to get parameter for (Components/Connections).

        label : str
            Label of the object in the TESPy model.

        parameter : str
            Name of the parameter of the object.

        Returns
        -------
        value : float
            Value of the parameter.
        """
        if obj == "Components":
            return self.nw.get_comp(label).get_attr(parameter).val
        elif obj == "Connections":
            return self.nw.get_conn(label).get_attr(parameter).val

    def set_params(self, **kwargs):

        if "Connections" in kwargs:
            for c, params in kwargs["Connections"].items():
                self.nw.get_conn(c).set_attr(**params)

        if "Components" in kwargs:
            for c, params in kwargs["Components"].items():
                self.nw.get_comp(c).set_attr(**params)
                
    def solve_model(self, **kwargs):
        """
        Solve the TESPy model given the input parameters
        """
        self.set_params(**kwargs)

        self.nw.solve("design", init_path=self._LB)

        if self.nw.status == 0:
            self._solved = True
        # is not required in this example, but could lead to handling some
        # stuff
        elif self.nw.status == 1:
            self._solved = False
        elif self.nw.status in [2, 3, 99]:
            # in this case model is very likely corrupted!!
            # fix it by running a presolve using the stable solution
            self._solved = False
            self.nw.solve("design", init_only=True, init_path=self._LB)

    def get_objectives(self, objective_list):
        """Get the objective values

        Parameters
        ----------
        objective_list : list
            Names of the objectives

        Returns
        -------
        list
            Values of the objectives
        """
        return [self.get_objective(obj) for obj in objective_list]

    def get_objective(self, objective=None):
        """
        Get the current objective function evaluation.

        Parameters
        ----------
        objective : str
            Name of the objective function.

        Returns
        -------
        objective_value : float
            Evaluation of the objective function.
        """
        if self._solved:
            if objective == "efficiency":
                return (
                    (self.nw.get_conn("e4").E.val-550-238)
                    / abs(self.nw.get_comp('economizer').Q.val + self.nw.get_comp('evaporator').Q.val)
                )
            
            elif objective == "production":
                return (
                    (self.nw.get_conn("e4").E.val-550-238)
                )
            
            elif objective == "heat":
                return abs(self.nw.get_comp('economizer').Q.val + self.nw.get_comp('evaporator').Q.val)
            
            else:
                msg = f"Objective {objective} not implemented."
                raise NotImplementedError(msg)
        else:
            return np.nan
        
# Defining the working fluid and call the design network
working_f = 'Isopentane'
case = Geo_ORC(working_f) 

"""
Optimisation using Pymoo results and validation though an idmax

"""

# State the optimisation objective from one of those implemented in get_objective
case.get_objective('production')

# Vary the pressure (p) at the evaporator outlet (c5)
variables = {"Connections": {"c5": {'p': {'min': 4, 'max': 12}}}}  # pressure in bar

# Inequality constraints , 
constraints = constraints = {
    "lower limits": {"Connections": {"w2": {"T": 70}}}
} # °C minimum re-injection temperature

# Track other values during the optimization
kpi = { "Components": {"turbine": {"P"},"pump": {"P"}},"Connections": {"c5":{"m"},"w2": {"T"} }} # T de la connexion w2 trackée


# --- Initialize the TESPy Optimization Problem ---
print("\n--- Setting up the Optimization Problem ---")

# pass the case to pymoo
problem = OptimizationProblem(case, variables, constraints=constraints, objective=["production"], minimize=[False], kpi=kpi) # minimize false give a maximizing function

# ---Run the Pymoo Optimizer ---

num_evo = 20  # Number of generations
algorithm = NRBO(pop_size=20) # Newton Raphson

print(f"\n--- Running Pymoo Optimization (Generations: {num_evo}) ---")
res = minimize(problem, algorithm,termination=('n_gen', num_evo),verbose=True)

# Visualization of the number of constraints and objectives given to the optimizer
print(problem)


# --- Process and Plots the Results without constraint---
print("\n--- Maximum without constraints (dataframe export & solve through .max() ) ---")

# TESPy's wrapper automatically logs everything into problem.log
result = pd.DataFrame(problem.log)

# Filter out non-converging runs (where production is NaN)
mask_objective = ~np.isnan(result["production"].values)
data = result.loc[mask_objective]

# Find the row with the best efficiency
best = data.loc[data["production"].values == data["production"].max()]

print("\n--- Best Parameters Found without constraint---")

print(best[["Connections-c5-p", "production", "Connections-w2-T"]]) 

# Sorting by pressure for a clean line plot
plot_data = data.sort_values("Connections-c5-p")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Net Power Output
ax1.plot(plot_data['Connections-c5-p'], plot_data['production'], color='tab:orange', linewidth=2, label='Evolution')
# Highlight the optimum found
ax1.scatter(best['Connections-c5-p'], best['production'], color='red', s=50, zorder=5, label='Optimum')

ax1.set_title('Net Power Output')
ax1.set_xlabel('Evaporation pressure [bar]')
ax1.set_ylabel('Net power output [kW]')
ax1.grid(True, linestyle='--', alpha=0.7)
ax1.set_ylim(4000, 6000) 
ax1.set_xlim(0, 14) 
ax1.legend()

# Plot 2: Flow Rate and Specific Enthalpy Drop
ax2_twin = ax2.twinx()
lns1 = ax2.plot(plot_data['Connections-c5-p'], plot_data['Connections-c5-m'], color='tab:orange', label='m_ORC')
# If you didn't track enthalpy specifically in KPIs, you can for example track Turbine Power and mass flow rate
lns2 = ax2_twin.plot(plot_data['Connections-c5-p'], -plot_data['Components-turbine-P']/plot_data['Connections-c5-m'], color='tab:blue', label='Dh_turb')

ax2.set_title('Flow rate and Enthalpy drop')
ax2.set_xlabel('Evaporation pressure [bar]')
ax2.set_ylabel('ORC mass flow rate [kg/s]')
ax2_twin.set_ylabel('Turbine enthalpy drop [kJ/kg]')
ax2.set_ylim(0, 200)
ax2_twin.set_ylim(0, 100)
ax2.set_xlim(0, 14)

# Combined legend
lns = lns1 + lns2
labs = [l.get_label() for l in lns]
ax2.legend(lns, labs, loc='center right')
ax2.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('Optimization.svg', format='svg', bbox_inches='tight')
plt.show()

# Plot 3: Water Exit Temperature (T_w2): visualization of existing pressures above the constraint
fig, ax3 = plt.subplots(figsize=(14, 5))

ax3.plot(plot_data['Connections-c5-p'], plot_data['Connections-w2-T'], color='tab:green', linewidth=2)
# Add a horizontal line for your constraint
ax3.axhline(y=70, color='red', linestyle='--', label='Constraint 70°C')

ax3.set_title('Water Exit Temperature ($T_{w2}$)')
ax3.set_xlabel('Evaporation pressure [bar]')
ax3.set_ylabel('Temperature [°C]')
ax3.grid(True, linestyle='--', alpha=0.7)
ax3.legend()

plt.tight_layout()
fig.savefig('water_exit_temperature.svg', format='svg', bbox_inches='tight')
plt.show()

# --- Printing the Best Result ---
# Using the 'best' dataframe row identified earlier
print("\n" + "="*40)
print(f"{'OPTIMIZATION RESULTS (max without constraint)':^40}")
print("="*40)
print(f"{'Optimal Evap. Pressure:':<25} {best['Connections-c5-p'].values[0]:>8.3f} bar")
print(f"{'Maximal Net Power:':<25} {best['production'].values[0]:>8.2f} kW")
print(f"{'Water Exit Temp (T_w2):':<25} {best['Connections-w2-T'].values[0]:>8.2f} °C")
print("="*40)




#--- Results from res (pymoo) with the constraint ---
print("\n--- The Optimization Problem using the constraint (export of the dataframe & solve through .idmax() )---")

# Get only values among those who respect the constraint of 70°C
valid_results = data[data["Connections-w2-T"] >= 70]

if not valid_results.empty:
    # Find the max production among those who respect the constraint of 70°C
    actual_best = valid_results.loc[valid_results["production"].idxmax()]
    
    print("\n--- CONSTRAINED OPTIMUM FOUND IN LOG ---")
    print(f"Optimal Pressure: {actual_best['Connections-c5-p']:.2f} bar")
    print(f"Production:       {actual_best['production']:.2f} kW")
    print(f"Water Exit T:     {actual_best['Connections-w2-T']:.2f} °C")
else:
    print("No points found above 70°C. Try widening the search.")

# --- Extracting the Official Pymoo Result ---
print("\n--- The Optimization Problem using the constraint (Using pymoo result matrices)---")

if res.X is not None:
    print("\n" + "="*40)
    print(f"{'OFFICIAL OPTIMIZER SOLUTION (using the constraint)':^40}")
    print("="*40)
    # res.X contains the optimized variables
    print(f"{'Optimal Pressure [bar]:':<25} {res.X[0]:>8.4f}")
    
    # res.F is the objective value (Production)
    # Pymoo was told to maximize
    final_prod = -res.F[0]
    print(f"{'Maximized Production [kW]:':<25} {final_prod:>8.2f}")
    
    # Check if constraints were violated (res.G <= 0 means success)
    if hasattr(res, 'G') and res.G is not None:
        print(f"{'Constraint Violation (G):':<25} {res.G[0]:>8.4f}")
    print("="*40)
else:
    print("\n[Warning] Pymoo found no feasible solution satisfying T_w2 >= 70°C.")


"""
Optional: fluprodia diagrams
"""

# Run the property diagrams
case.property_diagrams(working_f)

