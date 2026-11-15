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


        # implement constraints


sizes = {'S': 1, 'M': 2, 'L': 3}

#Constraint 1, aerobridge should at least be 80%
tot_pax = sum(a + d + t for a, d, t in zip(arrival_pass, departure_pass, transit_pass))
cont_pax = gb.quicksum(y[f, g] * (a + d + t) for f, a, d, t in zip(flights, arrival_pass, departure_pass, transit_pass) for g in c_gates)
model.addConstr(cont_pax >= (0.8 * tot_pax), name = 'contact gate pax rate')

# Constraint 2, safety time interval 
for i, fi in enumerate(flights):
    for j, fj in enumerate(flights):
        if i < j:
            dep_i = t_departure[i]
            arr_j = t_arrival[j]
            key = (fi, fj)

            for g in gates:
                model.addConstr(z[key] <= y[fi, g] + y[fj, g], name = f"Zlink{fi},{fj},{g}")

            model.addConstr(arr_j - dep_i + (1-z[key]) * M_big >= t_interval, name = f"timebuffer {fi}, {fj}")


# Constraint 3, gate can accomodate airplane size
for f, cap_f in zip(flights, aircraft_size):
    for g, cap_g in zip(gates, gate_size):
        if sizes[cap_f] > sizes[cap_g]:
            model.addConstr(y[f, g] == 0, name = f"compatibility {f}, {g}")

# Constraint 4, one and only one gate per flight
for f in flights:
    model.addConstr(gb.quicksum(y[f, g] for g in gates) == 1, name = f"gate_ass{f}")


        # choice menu for mode


print("select mode:")
print("1: Z1, 2: Z2, 3: Z1 with bound Z2")
choice = input("Enter mode (default: 3): ")

if choice == '1':
    mode = 'Z1'
    epsilon = None
elif choice == '2':
    mode = 'Z2'
    epsilon = None
else:
    mode = 'Z12'
    inp_epsilon = input("Enter espilon (default: 0.10): ")
    try:
        epsilon = float(inp_epsilon) if inp_epsilon else 0.10
    except ValueError:
        print("invalid epsilon (default epsilon 0.10): ")
        epsilon = 0.10


        # prepare objective function, make dict from all lists


d_arrival_dict = dict(zip(gates, d_arrival))
d_departure_dict = dict(zip(gates, d_departure))
d_transit_dict = dict(zip(gates, d_transit))

arrival_pass_dict = dict(zip(flights, arrival_pass))
departure_pass_dict = dict(zip(flights, departure_pass))
transit_pass_dict = dict(zip(flights, transit_pass))


        # implement objective function Z1 from equation 2
Z1_eq = gb.quicksum(y[f, g] * (arrival_pass_dict[f] * d_arrival_dict[g] + 
                               departure_pass_dict[f] * d_departure_dict[g] + 
                               transit_pass_dict[f] * d_transit_dict[g]) for f in flights for g in gates)


        # implement objective function Z2 from equation 6
al_tot_pax = {}
al_walk_eq = {}

for l in airlines:
    al_tot_pax[l] = sum(arrival_pass[flights.index(f)] + departure_pass[flights.index(f)] + transit_pass[flights.index(f)] 
                        for f in flights_airline[l])
    al_walk_eq[l] = gb.quicksum(y[f, g] * (arrival_pass_dict[f] * d_arrival_dict[g] + 
                                           departure_pass_dict[f] * d_departure_dict[g] + 
                                           transit_pass_dict[f] * d_transit_dict[g]
                                           )
                                           for f in flights_airline[l] for g in gates)

tot_pax_all = sum(al_tot_pax.values())


        # objective function basaed on mode choice
if mode == 'Z1':
    model.setObjective(Z1_eq, gb.GRB.MINIMIZE)
    print("mode 1, minimize pax walking distance")
elif mode == 'Z2':
    deviation = model.addVars(airlines, lb=0.0, vtype = gb.GRB.CONTINUOUS, name = "deviation")
    for l in airlines:
        share = al_tot_pax[l]/tot_pax_all
        model.addConstr(deviation[l] >= al_walk_eq[l] - share * Z1_eq, name = f'Positive_dev_{l}')
        model.addConstr(deviation[l] >= share * Z1_eq - al_walk_eq[l], name = f"Negative_dev_{l}")

    model.setObjective(gb.quicksum(deviation[l] for l in airlines), gb.GRB.MINIMIZE)
    print("mode 2, minimize airline unfairness")
elif mode == 'Z12':
    for l in airlines:
        share = al_tot_pax[l]/tot_pax_all
        model.addConstr(al_walk_eq[l] <= (1.0 + epsilon) * share * Z1_eq, name = f"upperbound_fairness_{l}")
        model.addConstr(al_walk_eq[l] >= (1.0 - epsilon) * share * Z1_eq, name = f"lowerbound_fairness_{l}")
    model.setObjective(Z1_eq, gb.GRB.MINIMIZE)


        # Solve and validate


model.optimize()
if model.status == gb.GRB.OPTIMAL:
    z1_out = Z1_eq.getValue()
    print()

        # visualize













# thisLHS = LinExpr()
# thisLHS += y[2]-y[0]+x[0]
# model.addConstr(lhs=thisLHS, sense=GRB.GREATER_EQUAL, rhs=ub_normal_length[0],
#                          name='A_C')

# thisLHS = LinExpr()
# thisLHS += y[9]-y[2]+x[2]
# model.addConstr(lhs=thisLHS, sense=GRB.GREATER_EQUAL, rhs=ub_normal_length[2],
#                          name='C_J')
