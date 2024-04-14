import subprocess
import os
import shutil
import time

# Path to the main_sta.py script
main_sta_path = 'C:/Users/Darshith/Documents/Codes/VLSI_Design_Automation_Projects/Project1/Phase2/src/main_sta.py'

# Directory containing the .bench files
bench_dir = 'C:/Users/Darshith/Documents/Codes/VLSI_Design_Automation_Projects/Project1/'

# Path to the NLDM library file
nldm_lib_path = 'C:/Users/Darshith/Documents/Codes/VLSI_Design_Automation_Projects/Project1/sample_NLDM.lib'

# Main output directory where results will be stored
output_dir = 'C:/Users/Darshith/Documents/Codes/VLSI_Design_Automation_Projects/Project1/output'

# Path to the directory whose contents you want to copy
source_dir = 'C:/Users/Darshith/Documents/Codes/VLSI_Design_Automation_Projects/Project1/Phase2/output'

# Create the main output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# List to keep track of files that showed errors during subprocess execution
files_with_errors = []

# Iterate over all files in the bench_dir directory
for filename in os.listdir(bench_dir):
    if filename.endswith('.bench'):
        # Extract the base name (without extension) to create a result directory path
        base_name = os.path.splitext(filename)[0]
        result_dir = os.path.join(output_dir, base_name)

        # Full path to the current .bench file
        bench_path = os.path.join(bench_dir, filename)

        # Construct the command to execute
        command = [
            'python', main_sta_path,
            '--read_nldm', nldm_lib_path, '--read_ckt', bench_path,
        ]

        # Execute the command within a try-except block
        try:
            start_time = time.time()
            subprocess.run(command, check=True)
            end_time = time.time()
            print(f"{base_name} - Time: {end_time-start_time}")

            # Create a directory for the results if it doesn't exist
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)

            # Copy the contents from source_dir to result_dir
            for item in os.listdir(source_dir):
                s = os.path.join(source_dir, item)
                d = os.path.join(result_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)  # For directories
                else:
                    shutil.copy2(s, d)  # For files

        except subprocess.CalledProcessError:
            # If an error occurs, add the filename to the list of files with errors
            files_with_errors.append(filename)

# After all files have been processed, check if there are any files with errors
if files_with_errors:
    print("The following files showed errors during execution:")
    for file in files_with_errors:
        print(file)
