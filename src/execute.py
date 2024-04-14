'''Executes main_sta.py for all the .bench files'''
import subprocess
import os
import shutil
import time

# Path to the main_sta.py script
MAIN_STA_PATH = './main_sta.py'

# Directory containing the .bench files
BENCH_DIR = '../bench'

# Path to the NLDM library file
NLDM_LIB_PATH = '../sample_NLDM.lib'

# Main output directory where results will be stored
OUTPUT_DIR = '../output'

# Path to the directory whose contents you want to copy
SOURCE_DIR = './output'

# Create the main output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# List to keep track of files that showed errors during subprocess execution
files_with_errors = []

# Iterate over all files in the BENCH_DIR directory
for filename in os.listdir(BENCH_DIR):
    if filename.endswith('.bench'):
        # Extract the base name (without extension) to create a result directory path
        base_name = os.path.splitext(filename)[0]
        result_dir = os.path.join(OUTPUT_DIR, base_name)

        # Full path to the current .bench file
        bench_path = os.path.join(BENCH_DIR, filename)

        # Construct the command to execute
        command = [
            'python', MAIN_STA_PATH,
            '--read_nldm', NLDM_LIB_PATH, '--read_ckt', bench_path,
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

            # Copy the contents from SOURCE_DIR to result_dir
            for item in os.listdir(SOURCE_DIR):
                s = os.path.join(SOURCE_DIR, item)
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
