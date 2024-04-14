import argparse
from pathlib import Path
import re
import os

# Class to store netlist's details
class Gates:
    def __init__(self):
        self.type = ""  # Type of logical gate
        self.name = ""  # Name of the gate in the circuit
        self.fanins = []    # List of fan-in of the node
        self.fanouts = []   # List of fan-out of the node
        self.input_slews = []   # Input slews of all the inputs
        self.output_slew = 0.0  # Output slew of the node
        self.input_arrival = [] # Inputs arrival time
        self.output_arrival = []    # Outputs arrival time
        self.max_output_arrival = 0.0   # Maximum output arrival time
      
# Class to store standard cell details
class Lib:
    def __init__(self):
        self.cell_name = "" # Standard cell name
        self.gate_type = "" # Logical gate type
        self.input_capacitance = 0  # Input capacitance
        self.input_slew = []    # Index 1 - Input slews
        self.output_load = []   # Index 2 - Output load
        self.delay = [] # 2D array of delays
        self.slew = [] # 2D array of slews

# Function to read netlist
def read_ckt(path):
    
    # Dictionary to store the count of different types of gates
    node_count = {}
    # Dictionary to store gate onjects of the circuit
    circuit = {}    
    
    # Iterae through all the lines of the netlist
    for line in path.open():

        # Skip lines having comments or empty lines
        if re.search(r"^#|^\s", line):
            continue
        
        # Finding the logical gate type
        node = re.search(r"(?:\s|)([a-zA-Z0-9]+)(?:\()", line).group(1)
        
        # Incrementing the node count
        node_count[node] = node_count.get(node, 0) + 1
        
        # Check if the node is a logical gate
        if node != "OUTPUT" and node != "INPUT":
            # Read inputs of the gate
            inputs_list = re.findall(r"(?<=\()(.*?)(?=\))", line)   
            inputs = re.split(',\s|,', inputs_list[0])
            # Read output of the gate
            output= re.search(r"(\w+)(:?\s=)", line).group(1)   
            # Create an object for Gates class if it doesnt exist already and store all the details
            if output not in circuit: 
                gate = Gates() 
                circuit[output] = gate     
            circuit[output].type = node
            circuit[output].name = node + "-" + output
            circuit[output].fanins = inputs[:]
            # Iterate through all the fan-ins of the circuit and assign fan-outs to those inputs
            for i in inputs:            
                # Check if the node already exists in dictionary. If not present, then create an object
                if i not in circuit:    
                    circuit[i] = Gates()
                circuit[i].fanouts.append(output)            

        # Check if the node is input
        elif node == "INPUT":   
            # Read net associated with input port
            net = re.search(r"[\(,](\w+)[,\)]", line).group(1)  
            # Create a class Gates object and store all the port details
            port = Gates()  
            port.type = node
            port.name = node + "-" + net
            port.output_slew = 0.002
            port.max_output_arrival = 0
            circuit[net] = port
        
        # Check if the node is output
        elif node == "OUTPUT":   
            # Read net associated with output port
            net = re.search(r"[\(,](\w+)[,\)]", line).group(1)
            # Check if the output already exists in the dictionary
            if f"{net}-o" not in circuit:
                # Create a class Gates object and store all the port details
                port = Gates()
                port.type = node
                port.name = node + "-" + net
                port.fanins.append(net)
                circuit[f"{net}-o"] = port
                # Check if the node already exists in dictionary. If not present, then create an object
                if net not in circuit:
                    circuit[net] = Gates()
                # Assign fan-out to the input node
                circuit[net].fanouts.append(f"{net}-o")
        
    # For the case of logical gates with dangling outputs, attach an output node
    for key, value in list(circuit.items()):    
        if len(value.fanouts)==0 and value.type != "OUTPUT":
            port = Gates()
            port.type = "OUTPUT"
            port.name = port.type + "-" + key
            port.fanins.append(key)
            circuit[f"{key}-o"] = port
            value.fanouts.append(f"{key}-o")

    # Create output directory if it doesnt exist
    output_path = "../output"
    if not os.path.isdir(output_path): os.makedirs(output_path)
    
    # Create a file to print circuit details
    result_file = open("../output/ckt_details.txt", "w")

    # Print count of inputs, outputs and logical gates
    for key, value in node_count.items():
        if str(key) != "INPUT" and str(key) != "OUTPUT":
            result_file.write(f"{value} {key} gates\n")
        else:
            result_file.write(f"{value} primary {key.lower()}s\n")
    
    # Print fan-out of all the gates
    result_file.write(f"\nFanout...\n")
    for key, value in circuit.items():
        if value.type != "INPUT" and len(value.fanouts)!=0:
            fanout_l = []
            for fanout in value.fanouts:               
                fanout_l.append(f"{circuit[fanout].name}")
            result_file.write(f"{value.name}: {', '.join(fanout_l)}\n")
            
    
    # Print fan-in of all the gates
    result_file.write(f"\nFanin...\n")
    for key, value in circuit.items():
        if value.type != "INPUT" and value.type != "OUTPUT":
            fanin_l = []
            for fanin in value.fanins:               
                fanin_l.append(f"{circuit[fanin].name}")
            result_file.write(f"{value.name}: {', '.join(fanin_l)}\n")
    
    result_file.close() # Close the file after printing all the values in the file

    return circuit

# Function to read .lib file
def read_nldm(path, delay_b=False, slews_b=False):

    # Dictionary to store all the standard cells
    gates = {}
    gate_count = 0

    for line in path.open():
        
        # Search for gate name in the line
        cell_name = re.search(r"(?:cell \()(.*)(?:\))", line)
        
        if cell_name is not None:
            gate_count += 1
            cell_name = cell_name.group(1)
            current_gate = re.search(r"(?<=cell \()([A-Z]+)(:?.*)", line)
            current_gate = current_gate.group(1)
            # Create an object Library and store standard cell's details
            gates[current_gate] = Lib()
            gates[current_gate].gate_type = current_gate
            gates[current_gate].cell_name = cell_name
        
        # Start checking for parameters only after the first standard cell is found
        if gate_count > 0:
            
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
    
    # Create delay file if delays are enabled in arguments
    if delay_b: result_file_delay = open("../output/delay_LUT.txt", "w")
    # Create slews file if delays are enabled in arguments 
    if slews_b: result_file_slew = open("../output/slew_LUT.txt", "w") 
    
    for key, value in gates.items():
        # Print delay values if delay argument is present
        if delay_b: 
            result_file_delay.write(f"cell: {value.cell_name}\n")
            result_file_delay.write(f"input slews: {','.join([str(i) for i in value.input_slew])}\n")
            result_file_delay.write(f"load cap: {','.join([str(i) for i in value.output_load])}\n\n")
            result_file_delay.write("delays:\n")
            for value_list in value.delay:
                result_file_delay.write(f"{','.join([str(i) for i in value_list])};\n")
            result_file_delay.write("\n")
        # Print slew values if slew argument is present
        if slews_b:
            result_file_slew.write(f"cell: {value.cell_name}\n")
            result_file_slew.write(f"input slews: {','.join([str(i) for i in value.input_slew])}\n")
            result_file_slew.write(f"load cap: {','.join([str(i) for i in value.output_load])}\n\n")
            result_file_slew.write("slews:\n")
            for value_list in value.slew:
                result_file_slew.write(f"{','.join([str(i) for i in value_list])};\n")
            result_file_slew.write("\n")
    
    # Close the delay file
    if delay_b: result_file_delay.close()
    # Close the slews file
    if slews_b: result_file_slew.close()

    # Handle cases with cells having different names
    gates["NOT"] = gates["INV"]
    gates["BUFF"] = gates["BUF"]

    return gates


# Function to parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    # Argument to read netlist
    parser.add_argument("--read_ckt", action = "store", help = "Provides details of the circuit.")
    # Argument to #print delays
    parser.add_argument("--delays", action = "store_true", help = "Creates a .txt file containing NLDM cell delays.")
    # Argument to #print slews
    parser.add_argument("--slews", action = "store_true", help = "Creates a .txt file containing NLDM output slews.")
    # Argument to read .lib files
    parser.add_argument("--read_nldm", action = "store", help = "Reads .lib files.")
    args = parser.parse_args()
    return args


def main():
    
    # Parse command line arguments
    inputs = parse_arguments()

    # Checks if the read_nldm argument is defined
    if inputs.read_nldm is not None:    
         # Path to the .lib file
        path = inputs.read_nldm
        path_lib = Path(path)
        # Checks if the .lib file exist
        if(path_lib.exists()):
            # Call read_nldm function if the .lib file exists, and pass delays and slews arguments to the function
            read_nldm(path_lib, inputs.delays, inputs.slews)
        else: print(".lib file doesn't exist.")
  
    # Checks if the read_ckt argument is defined
    if inputs.read_ckt is not None: 
        # Path to the netlist file
        path = inputs.read_ckt
        path_bench = Path(path)
        # Checks if the netlist file exists
        if(path_bench.exists()):
            # Call read_ckt function if the netlist exists
            read_ckt(path_bench)
        else: print(".bench file doesn't exist.")


if __name__ == '__main__':
    main()