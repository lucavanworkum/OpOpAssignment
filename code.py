#Imports
import numpy as np
import os
import pandas as pd
import time
import pickle
import gurobipy as gb


        # LOAD DATA


#Variables
file_path_flight = os.path.join(os.path.dirname(__file__), "data", "flight data.xlsx")
file_path_gate = os.path.join(os.path.dirname(__file__), "data", "gate data.xlsx")

M_big = 300

# Read the first three columns: flight, aircraft size, and airline.
flight_data = pd.read_excel(file_path_flight, sheet_name="Sheet1")
flights = flight_data.iloc[:, 0].tolist()
aircraft_size = flight_data.iloc[:, 1].tolist()
airline = flight_data.iloc[:, 2].tolist()

# Group flights by airline.
flights_airline = {}
for a in set(airline):
    flights_airline[a] = [
        flight for flight, flight_airline in zip(flights, airline)
        if flight_airline == a
    ]
#print(flights_airline)

gate_data = pd.read_excel(file_path_gate, sheet_name="Sheet1")
#gates = set of gates (10 in data of paper)
gates = gate_data.iloc[:, 0].tolist()
#gate_size = size of gate (S,M,L)
gate_size = gate_data.iloc[:, 1].tolist()

#t_arrival column 4
t_arrival = flight_data.iloc[:, 3].tolist()
#t_departure column 5
t_departure = flight_data.iloc[:, 4].tolist()
#t_interval: 15 mins between consecutive flights
t_interval = 15

#d_arrival: distance between arrival gate and bagage hall (column 3 of gate data)
d_arrival = gate_data.iloc[:, 2].tolist()
#d_departure: distance from security to departure gate (column 4 of gate data)
d_departure = gate_data.iloc[:, 3].tolist()
#d_transit: distance gate to transit counter (column 5 of gate data)
d_transit = gate_data.iloc[:, 4].tolist()

#gate_type: gate type, c for contact, r for remote stand
gate_type = gate_data.iloc[:, 6].tolist()
# print(gate_type)

#arrival_pass: number of passengers arriving at the airport (column 6 of flight data)
arrival_pass = flight_data.iloc[:, 5].tolist()
#departure_pass: number of passengers departing from the airport (column 7 of flight data)
departure_pass = flight_data.iloc[:, 6].tolist()
#transit_pass: number of passengers transiting through the airport (column 8 of flight data)
transit_pass = flight_data.iloc[:, 7].tolist()
#print(transit_pass)


        # PREPARE DATA


# function to change the time stamps to minutes
def time_to_min(t):
    if isinstance(t, str):
        time = list(map(int, t.split(':')))
        minutes = time[0] * 60 + time[1]
        return minutes
    elif hasattr(t, 'hour') and hasattr(t, 'minute'):
        minutes = t.hour * 60 + t.minute
        return minutes
    else:
        t_str = str(t).split()[-1]
        time = list(map(int, t_str.split(':')[:2]))
        minutes = time[0] * 60 + time[1]
        return minutes

# convert arrival time and departure time into minutes
t_arrival = [time_to_min(t) for t in t_arrival]
t_departure = [time_to_min(t) for t in t_departure]

# find the set of airlines
airlines = list(flights_airline.keys())

# make the distinction between contact and remote gates
c_gates = [g for g, t in zip(gates, gate_type) if t == 'C']
x_c_count = len(c_gates)


        #setup decisiion variables y(i,g_k) and z(fi, fj)
            # y(i,g_k) is the assignment of a flight to a gate, 1 if flight i is assigned to gate k, 0 otherwise
            # z(fi, fj) is the sequence var, 1 if flight i is assigned to the same gate as flight j, flight i arriving before j, needed for the safety time interval


model = gb.Model("Gate_Ass")

# first for var y
# y[f, g] = 1 if flight f assigned to gate g, 0 otherwise
y = model.addVars(flights, gates, vtype = gb.GRB.BINARY, name = 'y')  #use binary since either 0 or 1

# now for var z
# z[(fi, fj)] = 1 if fi and fj are assigned to the smae gate, 0 otherwise
pairs = [(flights[i], flights[j]) for i in range(len(flights)) for j in range(i+1, len(flights))]

z = model.addVars(pairs, vtype = gb.GRB.BINARY, name = 'z')

#update the model
model.update()


















# thisLHS = LinExpr()
# thisLHS += y[2]-y[0]+x[0]
# model.addConstr(lhs=thisLHS, sense=GRB.GREATER_EQUAL, rhs=ub_normal_length[0],
#                          name='A_C')

# thisLHS = LinExpr()
# thisLHS += y[9]-y[2]+x[2]
# model.addConstr(lhs=thisLHS, sense=GRB.GREATER_EQUAL, rhs=ub_normal_length[2],
#                          name='C_J')
