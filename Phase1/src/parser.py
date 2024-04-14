import argparse
from pathlib import Path
import re
import os

# Class to store netlist's details
class Gates:
    def __init__(self):
        self.type = ""  # Type of logical gate
        self.name = ""  # Name of the gate in the circuit
        self.fanins = []    # List of fan-in of the nodes
        self.fanouts = []   # List of fan-out of the nodes
        self.port_type = ""      # Type of port

# Class to store standard cell details
class Lib:
    def __init__(self):
        self.cell_name = "" # Standard cell name
        self.input_capacitance = 0  # Input capacitance
        self.input_slew = []    # Index 1 - Input slews
        self.output_load = []   # Index 2 - Output load
        self.delay = [] # 2D array of delays
        self.slew = [] # 2D array of slews

# Function to parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--read_ckt", action = "store", help = "Provides details of the circuit.")  # Argument to read netlist
    parser.add_argument("--delays", action = "store_true", help = "Creates a .txt file containing NLDM cell delays.")   # Argument to print delays
    parser.add_argument("--slews", action = "store_true", help = "Creates a .txt file containing NLDM output slews.")   # Argument to print slews
    parser.add_argument("--read_nldm", action = "store", help = "Reads .lib files.")    # Argument to read .lib files
    args = parser.parse_args()
    return args

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
                gate.type = node
                gate.name = node + "-" + output
                gate.fanins = inputs[:]
                circuit[output] = gate
            else:
                circuit[output].type = node
                circuit[output].name = node + "-" + output
                circuit[output].fanins = inputs[:]
            for i in inputs:            # Iterate through all the fan-ins of the circuit and assign fan-outs to those inputs
                if i not in circuit:    # Check if the node already exists in dictionary. If not present, then create an object
                    circuit[i] = Gates()
                    circuit[i].fanouts.append(output)
                elif circuit[i].type != "INPUT":
                    circuit[i].fanouts.append(output)
            if circuit[output].port_type == "OUTPUT":
                circuit[output].fanouts.append(output)
        else:   
            net = re.search(r"[\(,](\w+)[,\)]", line).group(1)  # Read net associated with input or output port
            port = Gates()  # Create a class Port object and store all the port details
            port.type = node
            port.name = node + "-" + net
            port.port_type = node
            circuit[net] = port
       
    # Create output directory if it doesnt exist
    output_path = "../output"
    if not os.path.isdir(output_path): os.makedirs(output_path)
    
    result_file = open("../output/ckt_details.txt", "w")   # Create a file to print circuit details

    # Print count of inputs, outputs and logical gates
    for key, value in node_count.items():
        if str(key) != "INPUT" and str(key) != "OUTPUT":
            result_file.write(f"{value} {key} gates\n")
        else:
            result_file.write(f"{value} primary {key.lower()}s\n")

    # Print fan-out of all the gates
    result_file.write(f"\nFanout...\n")
    for key, value in sorted(circuit.items()):
        if value.type != "INPUT" and value.type != "OUTPUT":
            fanout_l = []
            for fanout in value.fanouts:               
                if circuit[fanout].port_type == "OUTPUT" and fanout==key:
                    fanout_l.append(f"{circuit[fanout].port_type}-{fanout}")
                else:
                    fanout_l.append(f"{circuit[fanout].name}")
            result_file.write(f"{value.name}: {', '.join(fanout_l)}\n")
            
    
    # Print fan-in of all the gates
    result_file.write(f"\nFanin...\n")
    for key, value in sorted(circuit.items()):
        if value.type != "INPUT" and value.type != "OUTPUT":
            fanin_l = []
            for fanin in value.fanins:               
                fanin_l.append(f"{circuit[fanin].name}")
            result_file.write(f"{value.name}: {', '.join(fanin_l)}\n")
    
    result_file.close() # Close the file after printing all the values in the file

    

# Function to read .lib file
def read_nldm(path, delay_b, slews_b):

    gates = {}  # Dictionary to store all the standard cells
    gate_count = 0

    for line in path.open():
        
        gate = re.search(r"(?:cell \()(.*)(?:\))", line)    # Search for gate name in the line
        if gate != None:
            gate_count += 1
            current_gate = gate.group(1)
            gates[current_gate] = Lib() # Create an object Library and store it in dictionary
            gates[current_gate].cell_name = current_gate    # Update the cell name in the gate object
        
        if gate_count > 0:  # Start checking for parameters only after the first gate is found
            
            # Update the input capacitance in the gate object
            input_capacitance = re.search(r"(:?capacitance\s*:\s*)([\d.]+)", line)
            if input_capacitance != None:
                gates[current_gate].input_capacitance = input_capacitance.group(1)

            # Set flags to print cell delay
            cell_delay = re.search(r"cell_delay", line)
            if cell_delay != None:
                cell_delay_flag = True
                output_slew_flag = False

            # Set flags to print output slew
            output_slew = re.search(r"output_slew", line)
            if output_slew != None:
                cell_delay_flag = False
                output_slew_flag = True

            # Update the input slew list in the gate object
            input_slew_string = re.search(r"(?:index_1\s\(\")(.*)(?:\"\);)", line)
            if input_slew_string != None:
                inputs_slew_string_l = re.split(',\s|,', input_slew_string.group(1))
                input_slew = [float(i) for i in inputs_slew_string_l]
                gates[current_gate].input_slew = input_slew[:]

            # Update the output load list in the gate object
            output_load_string = re.search(r"(?:index_2\s\(\")(.*)(?:\"\);)", line)
            if output_load_string != None:
                output_load_string_l = re.split(',\s|,', output_load_string.group(1))
                output_load = [float(i) for i in output_load_string_l]
                gates[current_gate].output_load = output_load[:]
            
            # Print cell delay or output slew values based on the flags set before
            value_string = re.search(r"(?:values\s\(\" | \")(.*)(?:\",\s\\|\"\);)", line)
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
        if delay_b: # Print delay values if delay argument is present
            result_file_delay.write(f"cell: {value.cell_name}\n")
            result_file_delay.write(f"input slews: {','.join([str(i) for i in value.input_slew])}\n")
            result_file_delay.write(f"load cap: {','.join([str(i) for i in value.output_load])}\n\n")
            result_file_delay.write("delays:\n")
            for value_list in value.delay:
                result_file_delay.write(f"{','.join([str(i) for i in value_list])};\n")
            result_file_delay.write("\n")
        if slews_b: # Print slew values if slew argument is present
            result_file_slew.write(f"cell: {value.cell_name}\n")
            result_file_slew.write(f"input slews: {','.join([str(i) for i in value.input_slew])}\n")
            result_file_slew.write(f"load cap: {','.join([str(i) for i in value.output_load])}\n\n")
            result_file_slew.write("slews:\n")
            for value_list in value.slew:
                result_file_slew.write(f"{','.join([str(i) for i in value_list])};\n")
            result_file_slew.write("\n")

def main():
    
    inputs = parse_arguments()  # Parse command line arguments

    if inputs.read_ckt is not None: # Checks if the read_ckt argument is defined
        path = inputs.read_ckt  # Path to the netlist file
        path_bench = Path(path)
        if(path_bench.exists()):    # Checks if the netlist file exists
            read_ckt(path_bench)    # Call read_ckt function if the netlist exists
        else: print(".bench file doesn't exist.")   
    
    if inputs.read_nldm is not None:    # Checks if the read_nldm argument is defined
        path = inputs.read_nldm # Path to the .lib file
        path_lib = Path(path)
        if(path_lib.exists()):  # Checks if the .lib file exist
            read_nldm(path_lib, inputs.delays, inputs.slews)     # Call read_nldm function if the .lib file exists, and pass delays and slews arguments to the function
        else: print(".lib file doesn't exist.")


if __name__ == '__main__':
    main()