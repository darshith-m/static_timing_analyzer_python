Static Timing Analysis

### Directory:
```bash
.
├── src                     # Source folder
│   ├── parser.py           # The python script parses through netlist and lib files. 
├── output                  # Output folder
│   ├── ckt_details.txt     # Contains netlist details
│   ├── delay_LUT.txt       # Contains delays of standard cells
│   └── slew_LUT.txt        # Contains slews of standard cells
├── requirements.txt        # Required python libraries
└── README.md
```
### Commands:

1. Change the root directory to 'src' folder to execute the 'parser.py' file.
------------------------------------------------------------
    cd src
------------------------------------------------------------

2. Command to generate circuit details output file.
------------------------------------------------------------
    python3.7 parser.py --read_ckt <path/to/*.bench>
------------------------------------------------------------

3. Command to print delays of standard cells.
------------------------------------------------------------
    python3.7 parser.py --delays --read_nldm <path/to/*.lib>
------------------------------------------------------------

4. Command to print slews of standard cells.
------------------------------------------------------------
    python3.7 parser.py --slews --read_nldm <path/to/*.lib>
------------------------------------------------------------

