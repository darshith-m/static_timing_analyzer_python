import argparse
from pathlib import Path
import re
import os
import random
import time

# Class to store netlist's details
class Gates:
    def __init__(self):
        self.type = ""  # Type of logical gate
        self.name = ""  # Name of the gate in the circuit
        self.fanins = []    # List of fan-in of the nodes
        self.fanouts = []   # List of fan-out of the nodes
        self.input_slews = []
        self.output_slew = 0.0
        self.input_arrival = []
        self.output_arrival = []
        self.max_output_arrival = 0.0
      
# Class to store standard cell details
class Lib:
    def __init__(self):
        self.cell_name = "" # Standard cell name
        self.gate_type = ""
        self.input_capacitance = 0  # Input capacitance
        self.input_slew = []    # Index 1 - Input slews
        self.output_load = []   # Index 2 - Output load
        self.delay = [] # 2D array of delays
        self.slew = [] # 2D array of slews

# Function to read netlist
def read_ckt(path):
    
    node_count = {} # Dictionary to store the count of different types of gates
    circuit = {}    # Dictionary to store gate onjects of the circuit
    
    for line in path.open():

        if re.search(r"^#|^\s", line): # Skip lines having comments or empty lines
            continue
        
        node = re.search(r"(?:\s|)([a-zA-Z0-9]+)(?:\()", line).group(1) # Finding the logical gate type
        node_count[node] = node_count.get(node, 0) + 1  # Incrementing the node count
        
        if node != "OUTPUT" and node != "INPUT":
            inputs_list = re.findall(r"(?<=\()(.*?)(?=\))", line)   # Read inputs of the gate
            inputs = re.split(',\s|,', inputs_list[0])
            output= re.search(r"(\w+)(:?\s=)", line).group(1)   # Read output of the gate
            if output not in circuit: 
                gate = Gates()  # Create an object for Gates class and store all the details
                circuit[output] = gate
            circuit[output].type = node
            circuit[output].name = node + "-" + output
            circuit[output].fanins = inputs[:]
            for i in inputs:            # Iterate through all the fan-ins of the circuit and assign fan-outs to those inputs
                if i not in circuit:    # Check if the node already exists in dictionary. If not present, then create an object
                    circuit[i] = Gates()
                circuit[i].fanouts.append(output)            

        elif node == "INPUT":   
            net = re.search(r"[\(,](\w+)[,\)]", line).group(1)  # Read net associated with input or output port
            port = Gates()  # Create a class Port object and store all the port details
            port.type = node
            port.name = node + "-" + net
            port.output_slew = 0.002
            port.max_output_arrival = 0
            circuit[net] = port
    
    for key, value in list(circuit.items()):
        if len(value.fanouts) == 0:
            port = Gates()
            port.type = "OUTPUT"
            port.name = port.type + "-" + key
            port.fanins.append(key)
            circuit[f"{key}-o"] = port
            value.fanouts.append(f"{key}-o")

    # Create output directory if it doesnt exist
    output_path = "../output"
    if not os.path.isdir(output_path): os.makedirs(output_path)
    
    result_file = open("../output/ckt_details.txt", "w")   # Create a file to #print circuit details

    # #print count of inputs, outputs and logical gates
    for key, value in node_count.items():
        if str(key) != "INPUT" and str(key) != "OUTPUT":
            result_file.write(f"{value} {key} gates\n")
        else:
            result_file.write(f"{value} primary {key.lower()}s\n")
    
    # #print fan-out of all the gates
    result_file.write(f"\nFanout...\n")
    for key, value in circuit.items():
#       if value.type != "INPUT" and value.type != "OUTPUT":
            fanout_l = []
            for fanout in value.fanouts:               
                fanout_l.append(f"{circuit[fanout].name}")
            result_file.write(f"{value.name}: {', '.join(fanout_l)}\n")
            
    
    # #print fan-in of all the gates
    result_file.write(f"\nFanin...\n")
    for key, value in circuit.items():
#        if value.type != "INPUT" and value.type != "OUTPUT":
            fanin_l = []
            for fanin in value.fanins:               
                fanin_l.append(f"{circuit[fanin].name}")
            result_file.write(f"{value.name}: {', '.join(fanin_l)}\n")
    
    result_file.close() # Close the file after printing all the values in the file

    return circuit


    

# Function to read .lib file
def read_nldm(path, delay_b, slews_b):

    gates = {}  # Dictionary to store all the standard cells
    gate_count = 0

    for line in path.open():
        
        cell_name = re.search(r"(?:cell \()(.*)(?:\))", line)    # Search for gate name in the line
        
        if cell_name is not None:
            gate_count += 1
            cell_name = cell_name.group(1)
            current_gate = re.search(r"(?<=cell \()([A-Z]+)(:?.*)", line)
            current_gate = current_gate.group(1)
            gates[current_gate] = Lib() # Create an object Library and store it in dictionary
            gates[current_gate].gate_type = current_gate
            gates[current_gate].cell_name = cell_name    # Update the cell name in the gate object
        
        if gate_count > 0:  # Start checking for parameters only after the first gate is found
            
            # Update the input capacitance in the gate object
            input_capacitance = re.search(r"(?:capacitance\s*:\s*)([\d.]+)", line)
            if input_capacitance != None:
                input_capacitance = input_capacitance.group(1)
                input_capacitance = round(float(input_capacitance), 3)
                gates[current_gate].input_capacitance = input_capacitance
                continue

            # Set flags to #print cell delay
            cell_delay = re.search(r"cell_delay", line)
            if cell_delay != None:
                cell_delay_flag = True
                output_slew_flag = False
                continue

            # Set flags to #print output slew
            output_slew = re.search(r"output_slew", line)
            if output_slew != None:
                cell_delay_flag = False
                output_slew_flag = True
                continue

            # Update the input slew list in the gate object
            input_slew_string = re.search(r"(?:index_1\s\(\")(.*)(?:\"\);)", line)
            if input_slew_string != None:
                inputs_slew_string_l = re.split(',\s|,', input_slew_string.group(1))
                input_slew = [float(i) for i in inputs_slew_string_l]
                gates[current_gate].input_slew = input_slew[:]
                continue

            # Update the output load list in the gate object
            output_load_string = re.search(r"(?:index_2\s\(\")(.*)(?:\"\);)", line)
            if output_load_string != None:
                output_load_string_l = re.split(',\s|,', output_load_string.group(1))
                output_load = [float(i) for i in output_load_string_l]
                gates[current_gate].output_load = output_load[:]
                continue
            
            # #print cell delay or output slew values based on the flags set before
            value_string = re.search(r"(?:values\s\(\"|\")(.*)(?:\",\s\\|\"\);)", line)
            if value_string != None:
                value_string_l = re.split(',\s|,', value_string.group(1))
                values = [float(i) for i in value_string_l]
                if cell_delay_flag == True:
                    gates[current_gate].delay.append(values)
                if output_slew_flag == True:
                    gates[current_gate].slew.append(values)

    # Create output directory if it doesnt exist
    output_path = "../output"
    if not os.path.isdir(output_path): os.makedirs(output_path)
    
    if delay_b: result_file_delay = open("../output/delay_LUT.txt", "w")   # Create delay file if delays are enabled in arguments
    if slews_b: result_file_slew = open("../output/slew_LUT.txt", "w")   # Create slews file if delays are enabled in arguments  
    
    for key, value in gates.items():
        if delay_b: # #print delay values if delay argument is present
            result_file_delay.write(f"cell: {value.cell_name}\n")
            result_file_delay.write(f"input slews: {','.join([str(i) for i in value.input_slew])}\n")
            result_file_delay.write(f"load cap: {','.join([str(i) for i in value.output_load])}\n\n")
            result_file_delay.write("delays:\n")
            for value_list in value.delay:
                result_file_delay.write(f"{','.join([str(i) for i in value_list])};\n")
            result_file_delay.write("\n")
        if slews_b: # #print slew values if slew argument is present
            result_file_slew.write(f"cell: {value.cell_name}\n")
            result_file_slew.write(f"input slews: {','.join([str(i) for i in value.input_slew])}\n")
            result_file_slew.write(f"load cap: {','.join([str(i) for i in value.output_load])}\n\n")
            result_file_slew.write("slews:\n")
            for value_list in value.slew:
                result_file_slew.write(f"{','.join([str(i) for i in value_list])};\n")
            result_file_slew.write("\n")
    
    if delay_b: result_file_delay.close()
    if slews_b: result_file_slew.close()

    gates["NOT"] = gates["INV"]
    gates["BUFF"] = gates["BUF"]

    return gates

class STA():

    def __init__(self, std_cell, netlist):
        self.std_cell = std_cell
        self.netlist = netlist
        self.in_degree = {}
        self.out_degree = {}
        self.cell_delay = {}
        self.total_cell_delay = 0.0
        self.total_cell_delay_slack = 0.0
        self.back_traversal_arrival = {}
        self.slack = {}
        self.sorted_order = []
        self.final_critical_path = []
        for key, value in self.netlist.items():
            self.in_degree[key] = len(self.netlist[key].fanins)
            self.out_degree[key] = len(self.netlist[key].fanouts)
    
    def interpolation(self, v11, v12, v21, v22, t1, t2, c1, c2, t, c):
        term1 = v11*(c2-c)*(t2-t)
        term2 = v12*(c-c1)*(t2-t)
        term3 = v21*(c2-c)*(t-t1)
        term4 = v22*(c-c1)*(t-t1)
        numerator = term1 + term2 + term3 + term4
        denominator = (c2-c1) * (t2-t1)
        value = numerator/denominator
        return value
    
    def delay_lookup(self, node, input_slew, output_capacitance):
        row = None
        column = None
        node_type = self.netlist[node].type
        if input_slew in self.std_cell[node_type].input_slew:
            row = self.std_cell[node_type].input_slew.index(input_slew)
        elif input_slew > self.std_cell[node_type].input_slew[-1]:
            row = len(self.std_cell[node_type].input_slew) - 1
        if output_capacitance in self.std_cell[node_type].output_load:
            column = self.std_cell[node_type].output_load.index(output_capacitance)
        elif output_capacitance > self.std_cell[node_type].output_load[-1]:
            column = len(self.std_cell[node_type].output_load) - 1   
        if row != None and column != None:
            value = self.std_cell[node_type].delay[row][column]
            return value
        else:
            if input_slew > self.std_cell[node_type].input_slew[-1]:
                print("exceeded value")
                list_length = len(self.std_cell[node_type].input_slew)
                row1 = list_length - 2
                row2 = list_length - 1
            if output_capacitance > self.std_cell[node_type].output_load[-1]:
                print("exceeded value")
                list_length = len(self.std_cell[node_type].output_load)
                column1 = list_length - 2
                column2 = list_length - 1
            for i in range(len(self.std_cell[node_type].input_slew)-1):
                if input_slew >= self.std_cell[node_type].input_slew[i] and input_slew < self.std_cell[node_type].input_slew[i+1]:
                    row1 = i
                    row2 = i+1
                if output_capacitance >= self.std_cell[node_type].output_load[i] and output_capacitance < self.std_cell[node_type].output_load[i+1]:
                    column1 = i
                    column2 = i+1
            #print(f"{node}-delay_rows = {row1, row2}")
            #print(f"{node}-delay_columns = {column1, column2}")
            v11 = self.std_cell[node_type].delay[row1][column1]
            v12 = self.std_cell[node_type].delay[row1][column2]
            v21 = self.std_cell[node_type].delay[row2][column1]
            v22 = self.std_cell[node_type].delay[row2][column2]
            t1 = self.std_cell[node_type].input_slew[row1]
            t2 = self.std_cell[node_type].input_slew[row2]
            c1 = self.std_cell[node_type].output_load[column1]
            c2 = self.std_cell[node_type].output_load[column2]
            #print(f"{node}-delay_interpolation = {c1, c2, t1, t2, v11, v12, v21, v22}") 
            value = self.interpolation(v11, v12, v21, v22, t1, t2, c1, c2, input_slew, output_capacitance)
            return value

    def slew_lookup(self, node, input_slew, output_capacitance):
        row = None
        column = None
        node_type = self.netlist[node].type
        if input_slew in self.std_cell[node_type].input_slew:
            row = self.std_cell[node_type].input_slew.index(input_slew)
        elif input_slew > self.std_cell[node_type].input_slew[-1]:
            row = len(self.std_cell[node_type].input_slew) - 1
        if output_capacitance in self.std_cell[node_type].output_load:
            column = self.std_cell[node_type].output_load.index(output_capacitance)
        elif output_capacitance > self.std_cell[node_type].output_load[-1]:
            column = len(self.std_cell[node_type].output_load) - 1    
        if row != None and column != None:
            value = self.std_cell[node_type].slew[row][column]
            return value
        else:
            if input_slew > self.std_cell[node_type].input_slew[-1]:
                print("exceeded value")
                list_length = len(self.std_cell[node_type].input_slew)
                row1 = list_length - 2
                row2 = list_length - 1
            if output_capacitance > self.std_cell[node_type].output_load[-1]:
                print("exceeded value")
                list_length = len(self.std_cell[node_type].output_load)
                column1 = list_length - 2
                column2 = list_length - 1
            for i in range(len(self.std_cell[node_type].input_slew)-1):
                if input_slew >= self.std_cell[node_type].input_slew[i] and input_slew < self.std_cell[node_type].input_slew[i+1]:
                    row1 = i
                    row2 = i+1
                if output_capacitance >= self.std_cell[node_type].output_load[i] and output_capacitance < self.std_cell[node_type].output_load[i+1]:
                    column1 = i
                    column2 = i+1
            #print(f"{node}-slew_rows = {row1, row2}")
            #print(f"{node}-slew_columns = {column1, column2}")            
            v11 = self.std_cell[node_type].slew[row1][column1]
            v12 = self.std_cell[node_type].slew[row1][column2]
            v21 = self.std_cell[node_type].slew[row2][column1]
            v22 = self.std_cell[node_type].slew[row2][column2]
            t1 = self.std_cell[node_type].input_slew[row1]
            t2 = self.std_cell[node_type].input_slew[row2]
            c1 = self.std_cell[node_type].output_load[column1]
            c2 = self.std_cell[node_type].output_load[column2]
            #print(f"{node}-slew_interpolation = {c1, c2, t1, t2, v11, v12, v21, v22}") 
            value = self.interpolation(v11, v12, v21, v22, t1, t2, c1, c2, input_slew, output_capacitance)
            return value
    
    def forward_traversal(self):
        in_degree = self.in_degree.copy()
        queue = [node for node in in_degree if in_degree[node]==0]
        sorted_order = []
        while len(queue) != 0:
            node = queue.pop(0)
            sorted_order.append(node)
            if self.netlist[node].type in self.std_cell:
                for fanin in self.netlist[node].fanins:
                    self.netlist[node].input_slews.append(self.netlist[fanin].output_slew)
                    self.netlist[node].input_arrival.append(self.netlist[fanin].max_output_arrival)
                #print(f"{node}-input_slews = {self.netlist[node].input_slews}")
                #print(f"{node}-input_arrival = {self.netlist[node].input_arrival}")
                
                output_capacitance = 0.0
                for fanout in self.netlist[node].fanouts:
                    if self.netlist[fanout].type != "OUTPUT":
                        output_capacitance += self.std_cell[self.netlist[fanout].type].input_capacitance
                    else:
                        output_capacitance += (4 * self.std_cell["INV"].input_capacitance)
                #print(f"{node}-output_capacitance = {output_capacitance}")

                self.cell_delay[node] = []
                cell_transition = []
                for input_slew in self.netlist[node].input_slews:
                    delay = self.delay_lookup(node, input_slew, output_capacitance)
                    slew = self.slew_lookup(node, input_slew, output_capacitance)
                    if len(self.netlist[node].fanins) > 2:
                        delay *= (len(self.netlist[node].fanins) / 2) 
                        slew *= (len(self.netlist[node].fanins) / 2)

                    self.cell_delay[node].append(delay)
                    cell_transition.append(slew)
                
                #print(f"{node}-cell_delay = {self.cell_delay[node]}")
                #print(f"{node}-cell_delay = {self.cell_delay}")
                #print(f"{node}-cell_transition = {cell_transition}")

                for i in range(len(self.cell_delay[node])):
                    self.netlist[node].output_arrival.append(self.cell_delay[node][i] + self.netlist[node].input_arrival[i])
                #print(f"{node}-output_arrival = {self.netlist[node].output_arrival}")
                self.netlist[node].max_output_arrival = max(self.netlist[node].output_arrival)
                #print(f"{node}-max_output_arrival = {self.netlist[node].max_output_arrival}")
                max_arrival_out_index = self.netlist[node].output_arrival.index(self.netlist[node].max_output_arrival)
                self.netlist[node].output_slew = cell_transition[max_arrival_out_index]
                #print(f"{node}-output_slew = {self.netlist[node].output_slew}")

            elif self.netlist[node].type == "INPUT":
                
                output_capacitance = 0.0
                for fanout in self.netlist[node].fanouts:
                    if self.netlist[fanout].type != "OUTPUT":
                        output_capacitance += self.std_cell[self.netlist[fanout].type].input_capacitance
                    else:
                        output_capacitance += (4 * self.std_cell["INV"].input_capacitance)
                #print(f"{node}-output_capacitance = {output_capacitance}")

            elif self.netlist[node].type == "OUTPUT":
                fanin = self.netlist[node].fanins[0]
                self.netlist[node].max_output_arrival = self.netlist[fanin].max_output_arrival
                if self.total_cell_delay < self.netlist[fanin].max_output_arrival:
                    self.total_cell_delay = self.netlist[fanin].max_output_arrival

            self.total_cell_delay_slack = 1.1 * self.total_cell_delay 

            #print(f"{node}-total_cell_delay = {self.total_cell_delay}")
            #print(f"{node}-total_cell_delay_slack = {self.total_cell_delay_slack}")

            for neighbor in self.netlist[node].fanouts:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        self.sorted_order = sorted_order
        #print(sorted_order)

    def backward_traversal(self):
        out_degree = self.out_degree.copy()
        queue = [node for node in out_degree if out_degree[node]==0]
        sorted_order = []
        while len(queue) != 0:
            node = queue.pop(0)
            sorted_order.append(node)
            if self.netlist[node].type in self.std_cell:
                self.slack[node] = self.back_traversal_arrival[node] - self.netlist[node].max_output_arrival
                #print(f"{node}-slack = {self.slack[node]}")
                for i in range(len(self.netlist[node].fanins)):
                    fanin = self.netlist[node].fanins[i]
                    if (fanin in self.back_traversal_arrival):
                        if (self.back_traversal_arrival[fanin] > self.back_traversal_arrival[node]-self.cell_delay[node][i]):
                            self.back_traversal_arrival[fanin] = self.back_traversal_arrival[node] - self.cell_delay[node][i]
                            #print(f"{node}-{fanin}-Compared")
                            #print(f"{node}-back_traversal_arrival = {self.back_traversal_arrival[node]}")
                            #print(f"{node}-{fanin}-cell_delay = {self.cell_delay[node][i]}")
                            #print(f"{node}-{fanin}-back_traversal_arrival = {self.back_traversal_arrival[fanin]}")
                    else:
                        self.back_traversal_arrival[fanin] =  self.back_traversal_arrival[node] - self.cell_delay[node][i]
                        #print(f"{node}-{fanin}-back_traversal_arrival = {self.back_traversal_arrival[fanin]}")

            elif self.netlist[node].type == "INPUT":
                self.slack[node] = self.back_traversal_arrival[node] - self.netlist[node].max_output_arrival
                #print(f"{node}-back_traversal_arrival = {self.back_traversal_arrival[node]}")
                #print(f"{node}-max_output_arrival = {self.netlist[node].max_output_arrival}")
                #print(f"{node}-slack = {self.slack[node]}")


            elif self.netlist[node].type == "OUTPUT":
                self.back_traversal_arrival[node] =  self.total_cell_delay_slack
                self.slack[node] = self.back_traversal_arrival[node] - self.netlist[node].max_output_arrival
                fanin = self.netlist[node].fanins[0]
                self.back_traversal_arrival[fanin] = self.back_traversal_arrival[node]
                #print(f"{node}-{fanin}-back_traversal_arrival = {self.back_traversal_arrival[fanin]}")


            for neighbor in self.netlist[node].fanins:
                out_degree[neighbor] -= 1
                if out_degree[neighbor] == 0:
                    queue.append(neighbor)
        #print(sorted_order)

        result_file_slack = open("../output/ckt_traversal.txt", "w")   # Create delay file if delays are enabled in arguments
        result_file_slack.write(f"Circuit delay: {(self.total_cell_delay*1000):.5f} ps\n\n")
        
        for node in self.sorted_order:
            node_type = self.netlist[node].type
            if node_type != "OUTPUT":
                result_file_slack.write(f"{node_type}-{node}: {(self.slack[node]*1000):.5f}ps\n")
            else:
                result_file_slack.write(f"{node_type}-{self.netlist[node].fanins[0]}: {(self.slack[node]*1000):.5f}ps\n")
        result_file_slack.close()

    def critical_path(self):
        out_degree = self.out_degree.copy()
        outputs = [node for node in out_degree if out_degree[node]==0]
        lowest_slack = min([self.slack[node] for node in outputs])
        nodes_lowest_slack = [node for node in outputs if self.slack[node] == lowest_slack]
        random_node_min_slack = random.choice(nodes_lowest_slack)
        queue = []
        queue.append(random_node_min_slack)
        sorted_order = []
        while len(queue) != 0:
            node = queue.pop(0)
            sorted_order.append(node)
            if self.netlist[node].type == "INPUT":
                break
            elif self.netlist[node].fanins:
                node_min_slack_neighbor = self.netlist[node].fanins[0]
                min_slack_neighbor = self.slack[node_min_slack_neighbor]
                for neighbor in self.netlist[node].fanins[1:]:
                    if self.slack[neighbor] < min_slack_neighbor:
                        min_slack_neighbor = self.slack[neighbor]
                        node_min_slack_neighbor = neighbor
                queue.append(node_min_slack_neighbor)
        sorted_order.reverse()
        
        self.final_critical_path = sorted_order[:]
        print(self.final_critical_path)
        
        critical_path_file = open("../output/ckt_traversal.txt", "a")
        critical_path_file.write("\nCritical path:\n\n")
        
        critical_path_print_list = []
        for node in self.final_critical_path:
            node_type = self.netlist[node].type
            if node_type != "OUTPUT":
                critical_path_print_list.append(f"{node_type}-{node}")
            else:
                critical_path_print_list.append(f"{node_type}-{self.netlist[node].fanins[0]}")
        critical_path_file.write(",".join(critical_path_print_list))

        critical_path_file.close()
    
    def critical_path_forward(self):
        in_degree = self.in_degree.copy()
        inputs = [node for node in in_degree if in_degree[node]==0]
        lowest_slack = min([self.slack[node] for node in inputs])
        nodes_lowest_slack = [node for node in inputs if self.slack[node] == lowest_slack]
        random_node_min_slack = random.choice(nodes_lowest_slack)
        queue = []
        queue.append(random_node_min_slack)
        sorted_order = []
        while len(queue) != 0:
            node = queue.pop(0)
            sorted_order.append(node)
            if self.netlist[node].type == "OUTPUT":
                break
            elif self.netlist[node].fanouts:
                node_min_slack_neighbor = self.netlist[node].fanouts[0]
                min_slack_neighbor = self.slack[node_min_slack_neighbor]
                for neighbor in self.netlist[node].fanouts[1:]:
                    if self.slack[neighbor] < min_slack_neighbor:
                        min_slack_neighbor = self.slack[neighbor]
                        node_min_slack_neighbor = neighbor
                queue.append(node_min_slack_neighbor)
        #sorted_order.reverse()
        
        self.final_critical_path = sorted_order[:]
        print(self.final_critical_path)
        
        critical_path_file = open("../output/ckt_traversal.txt", "a")
        critical_path_file.write("\nCritical path:\n")
        
        critical_path_print_list = []
        for node in self.final_critical_path:
            node_type = self.netlist[node].type
            if node_type != "OUTPUT":
                critical_path_print_list.append(f"{node_type}-{node}")
            else:
                critical_path_print_list.append(f"{node_type}-{self.netlist[node].fanins[0]}")
        critical_path_file.write(",".join(critical_path_print_list))

        critical_path_file.close()

    def execute(self):
        self.forward_traversal()
        self.backward_traversal()
        self.critical_path_forward()



# Function to parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--read_ckt", action = "store", help = "Provides details of the circuit.")  # Argument to read netlist
    parser.add_argument("--delays", action = "store_true", help = "Creates a .txt file containing NLDM cell delays.")   # Argument to #print delays
    parser.add_argument("--slews", action = "store_true", help = "Creates a .txt file containing NLDM output slews.")   # Argument to #print slews
    parser.add_argument("--read_nldm", action = "store", help = "Reads .lib files.")    # Argument to read .lib files
    args = parser.parse_args()
    return args

def main():
    start_time = time.time()
    
    inputs = parse_arguments()  # Parse command line arguments

    if inputs.read_nldm is not None:    # Checks if the read_nldm argument is defined
        path = inputs.read_nldm # Path to the .lib file
        path_lib = Path(path)
        if(path_lib.exists()):  # Checks if the .lib file exist
            std_cell = read_nldm(path_lib, inputs.delays, inputs.slews)     # Call read_nldm function if the .lib file exists, and pass delays and slews arguments to the function
        else: print(".lib file doesn't exist.")

    
    if inputs.read_ckt is not None: # Checks if the read_ckt argument is defined
        path = inputs.read_ckt  # Path to the netlist file
        path_bench = Path(path)
        if(path_bench.exists()):    # Checks if the netlist file exists
            netlist = read_ckt(path_bench)    # Call read_ckt function if the netlist exists
        else: print(".bench file doesn't exist.")

    if std_cell != None and netlist != None:
        sta = STA(std_cell, netlist)
        sta.execute()
    
    end_time = time.time()
    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == '__main__':
    main()