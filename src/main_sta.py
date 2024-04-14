'''Perform Static Timing Analysis'''
import argparse
from pathlib import Path
import random
import os
import main_parser

class STA():
    '''Static Timing Analysis class'''
    def __init__(self, std_cell, netlist):
        self.std_cell = std_cell    # Standard cell
        self.netlist = netlist      # Netlist
        self.in_degree = {}         # Number of fan-ins of all the nodes
        self.out_degree = {}        # Number of fan-outs of all the nodes
        self.cell_delay = {}        # Cell delays of the nodes
        self.total_circuit_delay = 0.0     # Total circuit delay
        self.total_circuit_delay_slack = 0.0   # Required arrival time for the circuit
        self.back_traversal_arrival = {}    # Required arrival time for all the nodes
        self.slack = {}             # Slack of the nodes
        self.sorted_order = []      # Sorted order of the nodes
        self.final_critical_path = []   # Final critical path
        # Calculate number of inputs and outputs for a node
        for key in self.netlist:       
            self.in_degree[key] = len(self.netlist[key].fanins)
            self.out_degree[key] = len(self.netlist[key].fanouts)

    def interpolation(self, v11, v12, v21, v22, t1, t2, c1, c2, t, c):
        '''# Function to calculate 2D-interpolation'''
        term1 = v11*(c2-c)*(t2-t)
        term2 = v12*(c-c1)*(t2-t)
        term3 = v21*(c2-c)*(t-t1)
        term4 = v22*(c-c1)*(t-t1)
        numerator = term1 + term2 + term3 + term4
        denominator = (c2-c1) * (t2-t1)
        value = numerator/denominator
        return value

    def lookup_index(self, node, input_slew, output_capacitance):    
        '''Function to lookup indexes from '''
        node_type = self.netlist[node].type        
        # If the input slew is beyond lookup indexes, 
        # set the row1 and row2 to the last 2 rows of the lookup table
        if input_slew > self.std_cell[node_type].input_slew[-1]:
            list_length = len(self.std_cell[node_type].input_slew)
            row1 = list_length - 2
            row2 = list_length - 1
        # If the output capacitance is beyond lookup indexes, 
        # set the column1 and column2 to the last 2 columns of the lookup table
        if output_capacitance > self.std_cell[node_type].output_load[-1]:
            list_length = len(self.std_cell[node_type].output_load)
            column1 = list_length - 2
            column2 = list_length - 1
        # Find the range in between which input slews and output capacitance fits in lookup table
        for i in range(len(self.std_cell[node_type].input_slew)-1):
            if input_slew >= self.std_cell[node_type].input_slew[i] and input_slew < self.std_cell[node_type].input_slew[i+1]:
                row1 = i
                row2 = i+1
            if output_capacitance >= self.std_cell[node_type].output_load[i] and output_capacitance < self.std_cell[node_type].output_load[i+1]:
                column1 = i
                column2 = i+1       
        return row1, row2, column1, column2

    def lookup(self, node, input_slew, output_capacitance, delay=False, slew=False):
        '''Function to perform lookup operation'''
         # Get the required indexes for lookup
        row1, row2, column1, column2 = self.lookup_index(node, input_slew, output_capacitance)
        node_type = self.netlist[node].type
        # Indexes of input slew
        t1 = self.std_cell[node_type].input_slew[row1]
        t2 = self.std_cell[node_type].input_slew[row2]
        # Indexes of capacitance
        c1 = self.std_cell[node_type].output_load[column1]
        c2 = self.std_cell[node_type].output_load[column2]
        # Lookup for delay
        if delay:
            v11 = self.std_cell[node_type].delay[row1][column1]
            v12 = self.std_cell[node_type].delay[row1][column2]
            v21 = self.std_cell[node_type].delay[row2][column1]
            v22 = self.std_cell[node_type].delay[row2][column2]
        # Lookup for slew
        elif slew:
            v11 = self.std_cell[node_type].slew[row1][column1]
            v12 = self.std_cell[node_type].slew[row1][column2]
            v21 = self.std_cell[node_type].slew[row2][column1]
            v22 = self.std_cell[node_type].slew[row2][column2]
        # 2D-Interpolation result
        value = self.interpolation(v11, v12, v21, v22, t1, t2, c1, c2, input_slew, output_capacitance)
        return value

    def forward_traversal(self):
        '''# Function to perform forward traversal of netlist'''
        # Copy length of fanins to another variable
        in_degree = self.in_degree.copy()
        # Populate input nodes to start forward traversal
        queue = [node for node in in_degree if in_degree[node]==0]
        # Create a list to store sorted list
        sorted_order = []
        # Iterate through netlist until queue length is not zero
        while len(queue) != 0:
            # Get the first node from queue
            node = queue.pop(0)
            # Append node to sorted list
            sorted_order.append(node)
            # Check if the node is a logical gate
            if self.netlist[node].type in self.std_cell:
                for fanin in self.netlist[node].fanins:
                    self.netlist[node].input_slews.append(self.netlist[fanin].output_slew)
                    self.netlist[node].input_arrival.append(self.netlist[fanin].max_output_arrival)  
                # Calculate output capacitance for the node
                output_capacitance = 0.0
                for fanout in self.netlist[node].fanouts:
                    # If the node is not of output type, add it's standard cell's output capacitance
                    if self.netlist[fanout].type != "OUTPUT":
                        output_capacitance += self.std_cell[self.netlist[fanout].type].input_capacitance
                    # If the node is of output type, add 4 times the Inverter cell's input capacitance
                    else:
                        output_capacitance += (4 * self.std_cell["INV"].input_capacitance)
                self.cell_delay[node] = []
                cell_transition = []              
                # Perform lookups for delay and slew
                for input_slew in self.netlist[node].input_slews:
                    delay = self.lookup(node, input_slew, output_capacitance, delay=True)
                    slew = self.lookup(node, input_slew, output_capacitance, slew=True)
                    # If the node has more than 2 inputs, multiply delay and slew with 'number of inputs / 2'
                    if len(self.netlist[node].fanins) > 2:
                        delay *= len(self.netlist[node].fanins)/2
                        slew *= len(self.netlist[node].fanins)/2
                    # Store cell delay
                    self.cell_delay[node].append(delay)
                    cell_transition.append(slew)              
                # Calculate arrival times for all the inputs of the node
                for i in range(len(self.cell_delay[node])):
                    self.netlist[node].output_arrival.append(self.cell_delay[node][i] + self.netlist[node].input_arrival[i])          
                # Get the maximum output arrival time
                self.netlist[node].max_output_arrival = max(self.netlist[node].output_arrival)      
                # Get the maximum output arrival time index
                max_arrival_out_index = self.netlist[node].output_arrival.index(self.netlist[node].max_output_arrival)     
                # Get the output slew using maximum output arrival time index
                self.netlist[node].output_slew = cell_transition[max_arrival_out_index]  
            # Check if the node is input
            elif self.netlist[node].type == "INPUT":
                # Calculate output capacitance for the node
                output_capacitance = 0.0
                for fanout in self.netlist[node].fanouts:
                    # If the node is not of output type, add it's standard cell's output capacitance
                    fanout_type = self.netlist[fanout].type
                    if fanout_type != "OUTPUT":
                        output_capacitance += self.std_cell[fanout_type].input_capacitance
                    # If the node is output type, add 4 times the Inverter cell's input capacitance
                    else:
                        output_capacitance += (4 * self.std_cell["INV"].input_capacitance)
            # Check if the node is output
            elif self.netlist[node].type == "OUTPUT":
                # Get the first fan-in node of the node
                fanin = self.netlist[node].fanins[0]
                # Get the maximum output arrival of first fan-in node 
                self.netlist[node].max_output_arrival = self.netlist[fanin].max_output_arrival
                # Get the maximum of maximum output arrival time of output node, or the cell delay
                if self.total_circuit_delay < self.netlist[fanin].max_output_arrival:
                    self.total_circuit_delay = self.netlist[fanin].max_output_arrival
            # calculate the required arrival time
            self.total_circuit_delay_slack = 1.1 * self.total_circuit_delay 
            # Iterate through neighboring nodes
            for neighbor in self.netlist[node].fanouts:
                # Once the neighbor is visited, subtract 1 from its in_degree
                in_degree[neighbor] -= 1
                # If in_degree is zero, all the inputs are ready for the neighboring node, and it can be appended to the queue
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        # Store the sorted order
        self.sorted_order = sorted_order

    def backward_traversal(self):
        '''Function to perform backward traversal on netlist'''
        # Copy length of fanouts to another variable
        out_degree = self.out_degree.copy()
        # Populate output nodes to start back traversal
        queue = [node for node in out_degree if out_degree[node]==0]
        # Iterate through netlist until queue length is not zero
        while len(queue) != 0:  
            # Get the first node from queue
            node = queue.pop(0)
            # Check if the node is a logical gate
            if self.netlist[node].type in self.std_cell:
                # Calculate Slack for the node
                self.slack[node] = self.back_traversal_arrival[node] - self.netlist[node].max_output_arrival
                # Assign required arrival times to the fan-in nodes of the given node
                for i, fanin in enumerate(self.netlist[node].fanins):
                    if fanin in self.back_traversal_arrival:
                        if (self.back_traversal_arrival[fanin] > self.back_traversal_arrival[node]-self.cell_delay[node][i]):
                            self.back_traversal_arrival[fanin] = self.back_traversal_arrival[node] - self.cell_delay[node][i]
                    else:
                        self.back_traversal_arrival[fanin] =  self.back_traversal_arrival[node] - self.cell_delay[node][i]
            # Check if the node is input
            elif self.netlist[node].type == "INPUT":
                # Calculate Slack for the node
                self.slack[node] = self.back_traversal_arrival[node] - self.netlist[node].max_output_arrival
            # Check if the node is output
            elif self.netlist[node].type == "OUTPUT":
                # Assign required arrival time for output node
                self.back_traversal_arrival[node] =  self.total_circuit_delay_slack
                # Calculate Slack for the node
                self.slack[node] = self.back_traversal_arrival[node] - self.netlist[node].max_output_arrival
                # Assign required arrival time to the fan-in node of the given node
                fanin = self.netlist[node].fanins[0]
                self.back_traversal_arrival[fanin] = self.back_traversal_arrival[node]
            # Iterate through neighboring nodes
            for neighbor in self.netlist[node].fanins:
                # Once the neighbor is visited, subtract 1 from its out_degree
                out_degree[neighbor] -= 1
                # If out_degree is zero, output arrival time can be calculated for the node,
                #  and it can be appended to the queue
                if out_degree[neighbor] == 0:
                    queue.append(neighbor)
        # Create output directory if it doesnt exist
        output_path = "../output"
        if not os.path.isdir(output_path):
            os.makedirs(output_path)
        # Create a file to store the slack information of the netlist
        result_file_slack = open("../output/ckt_traversal.txt", "w")
        # Print the circuit delay
        result_file_slack.write(f"Circuit delay: {(self.total_circuit_delay*1000):.5f} ps\n\n")
        result_file_slack.write("Gate slacks:\n")
        # Iterate through all the nodes and print its slack
        for node in self.sorted_order:
            node_type = self.netlist[node].type
            if node_type != "OUTPUT":
                result_file_slack.write(f"{node_type}-{node}: {(self.slack[node]*1000):.5f} ps\n")
            else:
                result_file_slack.write(f"{node_type}-{self.netlist[node].fanins[0]}: {(self.slack[node]*1000):.5f} ps\n")
        # Close the file
        result_file_slack.close()

    def critical_path(self):
        '''Function to find the critical path of the netlist'''
        # Copy length of fanouts to another variable
        out_degree = self.out_degree.copy()
        # Populate output nodes to start back traversal
        outputs = [node for node in out_degree if out_degree[node]==0]
        # Find the output node with the least slack
        lowest_slack = min([self.slack[node] for node in outputs])
        # Check if multiples output nodes have same minimum slack
        nodes_lowest_slack = [node for node in outputs if self.slack[node] == lowest_slack]
        # Pick a random output node with same minimum slack
        random_node_min_slack = random.choice(nodes_lowest_slack)
        queue = []
        queue.append(random_node_min_slack)
        sorted_order = []
        # Iterate through netlist until queue length is not zero
        while len(queue) != 0:
            node = queue.pop(0)
            sorted_order.append(node)
            # If an input node is reached, stop the queue
            if self.netlist[node].type == "INPUT":
                break
            elif self.netlist[node].fanins:
                # Get the fan-in node with the least slack
                node_min_slack_neighbor = self.netlist[node].fanins[0]
                min_slack_neighbor = self.slack[node_min_slack_neighbor]
                for neighbor in self.netlist[node].fanins[1:]:
                    if self.slack[neighbor] < min_slack_neighbor:
                        min_slack_neighbor = self.slack[neighbor]
                        node_min_slack_neighbor = neighbor
                # Append the fan-in node with the last slack
                queue.append(node_min_slack_neighbor)
        # Reverse the path to get critical path from input to output node
        sorted_order.reverse()
        # Store the final critical path
        self.final_critical_path = sorted_order[:]
        # Append critical path to the file
        critical_path_file = open("../output/ckt_traversal.txt", "a", encoding="utf-8")
        critical_path_file.write("\nCritical path:\n")
        # Print critical path
        critical_path_print_list = []
        for node in self.final_critical_path:
            node_type = self.netlist[node].type
            if node_type != "OUTPUT":
                critical_path_print_list.append(f"{node_type}-{node}")
            else:
                critical_path_print_list.append(f"{node_type}-{self.netlist[node].fanins[0]}")
        critical_path_file.write(",".join(critical_path_print_list))
        # Close the file
        critical_path_file.close()

    def execute(self):
        '''Function to perform Static Timing Analysis'''
        # Step 1 - Perform forward traversal to check the circuit delay and required arrival time
        self.forward_traversal()
        # Step 2 - Perform backward traversal to calculate slack
        self.backward_traversal()
        # Step 3 - Perform backward traversal to find critical path
        self.critical_path()

def parse_arguments():
    '''# Function to parse command line arguments'''
    parser = argparse.ArgumentParser()
    # Argument to read netlist
    parser.add_argument("--read_ckt", action = "store", help = "Provides details of the circuit.")
    # Argument to read .lib files
    parser.add_argument("--read_nldm", action = "store", help = "Reads .lib files.")
    args = parser.parse_args()
    return args

def main():
    '''Main function of main_sta.py'''
    # Parse command line arguments
    inputs = parse_arguments()
    # Checks if the read_nldm argument is defined
    if inputs.read_nldm is not None:
        # Path to the .lib file
        path = inputs.read_nldm
        path_lib = Path(path)
        # Checks if the .lib file exist
        if path_lib.exists():
            # Call read_nldm function if the .lib file exists
            std_cell = main_parser.read_nldm(path_lib)
        else: print(".lib file doesn't exist.")
    # Checks if the read_ckt argument is defined
    if inputs.read_ckt is not None:
        # Path to the netlist file
        path = inputs.read_ckt
        path_bench = Path(path)
        # Checks if the netlist file exists
        if path_bench.exists():
            # Call read_ckt function if the netlist exists
            netlist = main_parser.read_ckt(path_bench)
        else:
            print(".bench file doesn't exist.")
    # Check if standard cell and netlist exists
    if std_cell is not None and netlist is not None:
        # Create an object of STA class, and initialize it with standard cell and netlist
        sta = STA(std_cell, netlist)
        # Perform Static Timing Analysis
        sta.execute()

if __name__ == '__main__':
    main()
