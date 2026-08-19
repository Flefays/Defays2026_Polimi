# -*- coding: utf-8 -*-
"""
Created on Wed Mar 11 17:03:10 2026

@author: flori

This code aims to simulate the LowBin project 

"""

"---Standard Imports---"

import numpy as np
from CoolProp.CoolProp import PropsSI as PSI

# To use dataframes (csv)
import pandas as pd

# To optimize
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

# Import the fluid and power components and connections 
from tespy.components import Source, Sink, CycleCloser, Pump, Turbine, MovingBoundaryHeatExchanger, HeatExchanger
from tespy.components import PowerBus, PowerSink, Motor, Generator
from tespy.connections import Connection, PowerConnection

"---LowBin model---"

class LowBin():
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
        
        "---Fluid Components"
        
        # Water Cycle
        w_su = Source('pumped water')
        w_ex = Sink('injected water')
        
        # Main Cycle
        cc = CycleCloser('cyclecloser')
        turb = Turbine('turbine')
        cond = MovingBoundaryHeatExchanger('condenser')
        pp = Pump('pump')
        preh = HeatExchanger('preheater')
        evap = MovingBoundaryHeatExchanger('evaporator')
        
        # Air Cycle
        a_su = Source('sucked air')
        a_ex = Sink('blown air')
        
        "---Fluid Connections---"
        
        # Water Cycle
        w0 = Connection(w_su, 'out1', evap, 'in1', label = 'w0')
        w1 = Connection(evap, 'out1', preh, 'in1', label = 'w1')
        w2 = Connection(preh, 'out1', w_ex, 'in1', label = 'w2')
        
        self.nw.add_conns(w0, w1, w2)
        
        # Main Cycle
        c0 = Connection(cc, 'out1', turb, 'in1', label= 'c0')
        c1 = Connection(turb, 'out1', cond, 'in1', label= 'c1')
        c2 = Connection(cond, 'out1', pp, 'in1', label= 'c2')
        c3 = Connection(pp, 'out1', preh, 'in2', label= 'c3')
        c4 = Connection(preh, 'out2', evap, 'in2', label= 'c4')
        c5 = Connection(evap, 'out2', cc, 'in1', label= 'c5')
        
        self.nw.add_conns(c0, c1, c2, c3, c4, c5)
        
        # Air Cycle
        a0 = Connection(a_su, 'out1', cond, 'in2', label = 'a0')
        a1 = Connection(cond, 'out2', a_ex, 'in1', label = 'a1')
       
        self.nw.add_conns(a0, a1)
        
        "---Electric Components---"
        
        # Energy Balance Maker
        ORC_bus = PowerBus('electricity bus of the ORC', num_in = 1, num_out = 2)
        
        # General Components
        ORC_grid = PowerSink('grid connection')
        motor = Motor('motor')
        generator = Generator('alternator')
        
        "---Electric Connections---"
        
        e0 = PowerConnection(turb, 'power', generator, 'power_in', label='e0')
        e1 = PowerConnection(generator, 'power_out', ORC_bus, 'power_in1', label='e1')
        e2 = PowerConnection(ORC_bus, 'power_out1', motor, 'power_in', label='e2')
        e3 = PowerConnection(motor, 'power_out', pp, 'power', label='e3')
        e4 = PowerConnection(ORC_bus, 'power_out2', ORC_grid, 'power', label='e4')
       
        self.nw.add_conns(e0, e1, e2, e3, e4)
        
        "---Parametrisation---"
        
        # 1st parametrisation using the turbine generation and pump consumption
        
        # Fluid definitions
        w_f = {'water': 1}  # {'fluid': massic fraction}
        a_f = {'air': 1}  # {'fluid': massic fraction}
        
        # Water Cycle
        w0.set_attr(fluid = w_f, m = 48.59, p = 5, T = 80)
        w1.set_attr(h0 = PSI("H", "T", 57 + 273.15, "Q", 0.0, 'water')/1e3 )
        w2.set_attr(T = 64.33)
        
        # Main Cycle
        c0.set_attr(fluid = {working_f:1}, m = 16, p = 16.782, T = 63.75) # LowBin work in superheated state, x can't be used. 
        c1.set_attr(p = 7.642); c2.set_attr(T0 = 26); c4.set_attr(T = 57)

        # Air Cycle
        a0.set_attr(fluid = a_f, m = 300, p = 1, T = 15)
        
        # Components
        evap.set_attr(pr1 = 4.49/5, pr2 = 16.782/16.88)
        preh.set_attr(pr1 = 4.15/4.49, pr2 = 16.88/17.26)
        cond.set_attr(pr1 = 7.272/7.642, pr2 = 1) 
        turb.set_attr(P = - 200.745)
        pp.set_attr(P = 19.820)
        
        # Power
        generator.set_attr(eta = 1)
        motor.set_attr(eta = 1)
        
        self.nw.solve('design')
        self.nw.print_results()
        
        # 2nd parametrisation using previous parametrisation isentropic efficiencies 
        c0.set_attr(T = None, td_dew = c0.td_dew.val)
        
        turb.set_attr(P = None, eta_s = turb.eta_s.val)
        pp.set_attr(P = None, eta_s = pp.eta_s.val)
        
        c4.set_attr(T = None)
        evap.set_attr(ttd_l = evap.ttd_l.val) # td_pinch = 8.55 or ttd_l = 11.1, but avoid using 2 geometrical constraints
        
        c1.set_attr(p = None, p0 = 7.642)
        cond.set_attr(td_pinch = cond.td_pinch.val) # td_pinch = 4.95 go to low in exhaust temperature, will try with ttdl
        
        self.nw.solve('design')
        self.nw.print_results()
    
        plot_tq_MBHX_SHX(evap, 'Evaporator')
        plot_tq_HX(preh, 'Preheater')
        plot_tq_MBHX_SHX(cond, 'Condenser')
        
        "---Power & Efficiency of the previous parametrization---"

        Net_Power = e4.E.val-33 # evaporative coolers consumption
        Net_Heat  = abs(preh.Q.val + evap.Q.val)
        Th_eff    = (Net_Power/Net_Heat)*100

        print(f"Net Power  : {Net_Power:.2f} kW", f"Net Heat   : {Net_Heat:.2f} kW", f"Efficacité : {Th_eff:.2f} %")
       
        # Save objects to 'self' so they are accessible in other methods
        self.c0 = c0
        self.e4 = e4
        self.turb = turb
        self.pp = pp
        self.cond = cond
        self.evap = evap
        self.preh = preh
        self.Net_Power = Net_Power
        
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
            "Preheater": self.nw.get_comp('preheater').get_plotting_data()[2],
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
                    (self.nw.get_conn("e4").E.val-33)
                    / abs(self.nw.get_comp('preheater').Q.val + self.nw.get_comp('evaporator').Q.val)
                )
            
            elif objective == "production":
                return (
                    (self.nw.get_conn("e4").E.val-33)
                )
            
            elif objective == "heat":
                return abs(self.nw.get_comp('preheater').Q.val + self.nw.get_comp('evaporator').Q.val)
            
            else:
                msg = f"Objective {objective} not implemented."
                raise NotImplementedError(msg)
        else:
            return np.nan
        
# Defining the working fluid and call the LowBin design network
working_f = 'R134a'
case = LowBin(working_f) 

# Run the property diagrams
case.property_diagrams(working_f)

# Choose the objective
case.get_objective('production')

# Vary the mass flow (m) and pressure (p) at the turbine inlet (c0)
variables = {"Connections": {"c0": {'p': {'min': 10, 'max': 35}}}} # pressure in bar

# They is no specific inequality constraints for this simple maximization, 
constraints = {}

# Track the turbine power and pump power during the optimization
kpi = {"Components": {"turbine": {"P"},"pump": {"P"}},
    "Connections": {
        "c2": {"T"},  # Temperature at condenser outlet
        "w2": {"T"}   # Temperature of geofluid reinjection
    }}

# --- Initialize the TESPy Optimization Problem ---

print("\n--- Setting up the Optimization Problem ---")
# pass your 'case' instance (the LowBin plant) to the problem
problem = OptimizationProblem(
    case, 
    variables, 
    constraints, 
    objective=["production"], 
    minimize=[False], # minimize false give a maximizing function
    kpi=kpi
)

# ---Run the Pymoo Optimizer ---

num_evo = 20  # Number of generations
algorithm = NRBO(pop_size=20) # Newton Raphson

print(f"\n--- Running Pymoo Optimization (Generations: {num_evo}) ---")
res = minimize(
    problem,
    algorithm,
    termination=('n_gen', num_evo),
    verbose=True
)

# --- 4. Process and Plot the Results ---

# TESPy's wrapper automatically logs everything into problem.log
result = pd.DataFrame(problem.log)

# Filter out non-converging runs (where production is NaN)
mask_objective = ~np.isnan(result["production"].values)
data = result.loc[mask_objective]

# Find the row with the best efficiency
best = data.loc[data["production"].values == data["production"].max()]

print("\n--- Best Parameters Found ---")
print(best[["Connections-c0-p", "production", "Connections-c2-T", "Connections-w2-T"]]) 


      
        