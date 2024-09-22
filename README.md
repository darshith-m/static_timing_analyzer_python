# Static Timing Analysis

### Directory:
```bash
.
├── src                     # Source folder
|   ├── execute.py          # The python script runs all the netlist required to be executed.
│   ├── main_parser.py      # The python script parses through netlist and lib files.
│   └── main_sta.py         # The python script performs static timing analysis and gets critical path
├── output                  # Output folder
│   ├── ckt_details.txt     # Contains netlist details
│   ├── ckt_traversal.txt   # Contains circuit delay, slack at each gate, and critical path
│   ├── delay_LUT.txt       # Contains delays of standard cells
│   └── slew_LUT.txt        # Contains slews of standard cells
├── requirements.txt        # Required python libraries
└── README.txt	 	    
```

### Commands:

1. Change the root directory to 'src' folder to execute the 'parser.py' file.
------------------------------------------------------------
    cd src
------------------------------------------------------------

2. Command to generate circuit details output file.
------------------------------------------------------------
    python3.7 parser_sta.py --read_ckt <path/to/*.bench>
------------------------------------------------------------

3. Command to print delays of standard cells.
-----------------------------------------------------------------
    python3.7 parser_sta.py --delays --read_nldm <path/to/*.lib>
-----------------------------------------------------------------

4. Command to print slews of standard cells.
----------------------------------------------------------------
    python3.7 parser_sta.py --slews --read_nldm <path/to/*.lib>
----------------------------------------------------------------

5. Command to perform static timing analysis.
----------------------------------------------------------------------------------
    python3.7 main_sta.py --read_nldm <path/to/*.lib> --read_ckt <path/to/*.bench>
----------------------------------------------------------------------------------


