import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import threading
from queue import Queue
import logging
import os
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Contract Vulnerability Scanner")
        self.geometry("800x1050")

        # Version list
        self.version_list = [
            "0.4.0", "0.4.1", "0.4.2", "0.4.3", "0.4.4", "0.4.5", "0.4.6", "0.4.7", "0.4.8", "0.4.9",
            "0.4.10", "0.4.11", "0.4.12", "0.4.13", "0.4.14", "0.4.15", "0.4.16", "0.4.17", "0.4.18", "0.4.19",
            "0.4.20", "0.4.21", "0.4.22", "0.4.23", "0.4.24", "0.4.25", "0.4.26", "0.5.0", "0.5.1", "0.5.2",
            "0.5.3", "0.5.4", "0.5.5", "0.5.6", "0.5.7", "0.5.8", "0.5.9", "0.5.10", "0.5.11", "0.5.12",
            "0.5.13", "0.5.14", "0.5.15", "0.5.16", "0.5.17", "0.6.0", "0.6.1", "0.6.2", "0.6.3", "0.6.4",
            "0.6.5", "0.6.6", "0.6.7", "0.6.8", "0.6.9", "0.6.10", "0.6.11", "0.6.12", "0.7.0", "0.7.1",
            "0.7.2", "0.7.3", "0.7.4", "0.7.5", "0.7.6", "0.8.0", "0.8.1", "0.8.2", "0.8.3", "0.8.4",
            "0.8.5", "0.8.6", "0.8.7", "0.8.8", "0.8.9", "0.8.10", "0.8.11", "0.8.12", "0.8.13", "0.8.14",
            "0.8.15", "0.8.16", "0.8.17", "0.8.18", "0.8.19", "0.8.20", "0.8.21", "0.8.22", "0.8.23", "0.8.24",
            "0.8.25", "0.8.26", "0.8.27", "0.8.28"
        ]

        self.version_var = tk.StringVar()
        self.version_var.set(self.version_list[0])

        self.version_dropdown = ttk.Combobox(self, textvariable=self.version_var)
        self.version_dropdown['values'] = self.version_list
        self.version_dropdown.pack(pady=10)

        self.button_frame = tk.Frame(self)
        self.button_frame.pack(pady=10)

        self.change_button = tk.Button(self.button_frame, text="Change Solc Version", command=self.change_solc_version)
        self.change_button.pack(side=tk.LEFT, padx=5)

        self.select_button = tk.Button(self.button_frame, text="Select Contract", command=self.select_contract)
        self.select_button.pack(side=tk.LEFT, padx=5)

        # Static Scanners Section
        static_scanners_frame = tk.Frame(self.button_frame)
        static_scanners_frame.pack(side=tk.LEFT, padx=10)

        self.scan_slither_button = tk.Button(static_scanners_frame, text="Scan with Slither", 
                                         command=self.scan_contract_slither, 
                                         bg="#87CEFA", fg="white")
        self.scan_slither_button.pack(side=tk.TOP, pady=5)

        self.scan_mythril_button = tk.Button(static_scanners_frame, text="Scan with Mythril", 
                                            command=self.scan_contract_mythril,
                                            bg="#FFA07A", fg="black")
        self.scan_mythril_button.pack(side=tk.TOP, pady=5)

        self.scan_solcscan_button = tk.Button(static_scanners_frame, text="Scan with Solcscan", 
                                          command=self.scan_with_solcscan, 
                                          bg="#90EE90", fg="black")
        self.scan_solcscan_button.pack(side=tk.TOP, pady=5)

        self.falcon_scan_button = tk.Button(static_scanners_frame, text="Scan with Falcon", 
                                         command=self.scan_falcon, bg="#FF6347", fg="white")
        self.falcon_scan_button.pack(side=tk.TOP, pady=5)

        self.wake_scan_button = tk.Button(static_scanners_frame, text="Scan with Wake", 
                                        command=self.scan_with_wake, bg="#32CD32", fg="white")
        self.wake_scan_button.pack(side=tk.TOP, pady=5)

        # Dynamic Scanners Section
        dynamic_scanners_frame = tk.Frame(self.button_frame)
        dynamic_scanners_frame.pack(side=tk.LEFT, padx=10)

        self.scan_aderyn_button = tk.Button(dynamic_scanners_frame, text="Scan with Aderyn", 
                                          command=self.scan_with_aderyn,
                                          bg="#FFA500", fg="black")
        self.scan_aderyn_button.pack(side=tk.TOP, pady=5)

        self.forge_test_button = tk.Button(dynamic_scanners_frame, text="Run Forge Test", 
                                       command=self.run_forge_test, 
                                       bg="#4B0082", fg="white")
        self.forge_test_button.pack(side=tk.TOP, pady=5)

        self.forge_setup_helper_button = tk.Button(self.button_frame, text="Forge Setup Helper", 
                                                   command=self.open_forge_setup_helper,
                                                   bg="#90EE90", fg="black")
        self.forge_setup_helper_button.pack(side=tk.LEFT, padx=5)

        self.output_text = tk.Text(self, height=30, width=80)
        self.output_text.pack(pady=10, fill=tk.BOTH, expand=True)

        self.queue = Queue()
        self.update_output()

    def update_output(self):
        try:
            while True:
                text = self.queue.get_nowait()
                self.output_text.insert(tk.END, text)
                self.output_text.yview(tk.END)
        except:
            pass
        finally:
            self.after(100, self.update_output)
    def change_solc_version(self):
        self.clear_output()
        version = self.version_var.get()
        command = f"solc-select use {version}"
        self.run_command(command)
        self.queue.put(f"Selected Solc version: {version}\n")

    def select_contract(self):
        self.clear_output()
        filename = filedialog.askopenfilename(filetypes=[("Solidity files", "*.sol")])
        if filename:
            self.contract_name = os.path.basename(filename).split('.')[0]
            self.selected_contract = filename
            self.queue.put(f"Selected contract: {self.contract_name}\n")

    def scan_contract_slither(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            slither_command = f"slither {self.selected_contract}"
            self.queue.put(f"Scanning contract with Slither: {self.selected_contract}\n")
            self.run_command(slither_command)
        else:
            self.queue.put("No contract selected for Slither scan.\n")

    def scan_contract_mythril(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            mythril_command = f"myth analyze {self.selected_contract}"
            self.queue.put(f"Scanning contract with Mythril: {self.selected_contract}\n")
            self.run_command(mythril_command)
        else:
            self.queue.put("No contract selected for Mythril scan.\n")

    def create_custom_terminal(self):
        self.custom_terminal = tk.Text(self.forge_helper_window, height=30, width=80)
        self.custom_terminal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.button_frame = tk.Frame(self.forge_helper_window)
        self.button_frame.pack(pady=10)

        self.change_dir_button = tk.Button(self.button_frame, text="Change Directory", 
                                           command=self.change_directory)
        self.change_dir_button.pack(side=tk.LEFT, padx=5)

        self.create_test_button = tk.Button(self.button_frame, text="Create Test File", 
                                           command=self.create_test_file)
        self.create_test_button.pack(side=tk.LEFT, padx=5)

        self.forge_build_button = tk.Button(self.button_frame, text="Forge Build", 
                                           command=self.run_forge_build)
        self.forge_build_button.pack(side=tk.LEFT, padx=5)

        self.forge_build_button = tk.Button(self.button_frame, text="Forge Test", 
                                           command=self.run_forge_test)
        self.forge_build_button.pack(side=tk.LEFT, padx=5)


        self.forge_install_button = tk.Button(self.button_frame, text="Forge Install", 
                                             command=self.run_forge_install)
        self.forge_install_button.pack(side=tk.LEFT, padx=5)

        self.git_init_button = tk.Button(self.button_frame, text="Git Init", 
                                        command=self.run_git_init)
        self.git_init_button.pack(side=tk.LEFT, padx=5)

        self.openzeppelin_install_button = tk.Button(self.button_frame, text="Install OpenZeppelin", 
                                                    command=self.run_forge_openzeppelin_install)
        self.openzeppelin_install_button.pack(side=tk.LEFT, padx=5)

        self.forge_init_new_project_button = tk.Button(self.button_frame, text="Forge Init New Project", 
                                                     command=self.forge_init_new_project)
        self.forge_init_new_project_button.pack(side=tk.LEFT, padx=5)

        self.run_command_button = tk.Button(self.button_frame, text="Run Command", 
                                          command=lambda: self.run_command_from_input())
        self.run_command_button.pack(side=tk.LEFT, padx=5)

        self.clear_output_button = tk.Button(self.button_frame, text="Clear Output", 
                                           command=self.clear_custom_output)
        self.clear_output_button.pack(side=tk.LEFT, padx=5)

        self.custom_input = tk.Entry(self.forge_helper_window, width=60)
        self.custom_input.pack(pady=5)

    def run_command_from_input(self):
        command = self.custom_input.get()
        self.run_command(command)

    def clear_custom_output(self):
        self.custom_terminal.delete('1.0', tk.END)

    def update_custom_output(self, text):
        self.custom_terminal.insert(tk.END, text)
        self.forge_helper_window.update_idletasks()


    def run_command(self, command):
        def target():
            self.update_custom_output(f"Executing command: {command}\n")
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                self.update_custom_output(result.stdout)
            except subprocess.CalledProcessError as e:
                self.update_custom_output(f"Command failed with exit code {e.returncode}\n")
                self.update_custom_output(f"Error: {e.output}")

        thread = threading.Thread(target=target)
        thread.start()
    def run_command(self, command):
        def target():
            self.update_custom_output(f"Executing command: {command}\n")
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                self.update_custom_output(result.stdout)
            except subprocess.CalledProcessError as e:
                self.update_custom_output(f"Command failed with exit code {e.returncode}\n")
                self.update_custom_output(f"Error: {e.output}")

        thread = threading.Thread(target=target)
        thread.start()

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)

    def scan_with_solcscan(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            import os

            # Define BASE_DIR based on the selected contract
            BASE_DIR = os.path.dirname(os.path.abspath(self.selected_contract))
            
            # Change to the contract's directory
            os.chdir(BASE_DIR)
            
            # Construct the Solcscan command using the full path to main.py
            solcscan_command = f"/usr/bin/python3 /home/robotics345/solscan/main.py scan {os.path.basename(self.selected_contract)}"
            self.queue.put(f"Solcscan command: {solcscan_command}\n")
            self.queue.put(f"Scanning contract with Solcscan: {self.selected_contract}\n")
            self.run_command(solcscan_command)
        else:
            self.queue.put("No contract selected for Solcscan scan.\n")

    def scan_falcon(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            falcon_command = f"python3 -m falcon {self.selected_contract}"
            self.queue.put(f"Scanning contract with Falcon: {self.selected_contract}\n")
            self.run_command(falcon_command)
        else:
            self.queue.put("No contract selected for Falcon scan.\n")

    def scan_with_wake(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            import os

            # Define BASE_DIR based on the selected contract
            BASE_DIR = os.path.dirname(os.path.abspath(self.selected_contract))
            
            # Change to the contract's directory
            os.chdir(BASE_DIR)
            
            # Construct the Wake command
            wake_command = f"wake detect all {os.path.basename(self.selected_contract)}"
            self.queue.put(f"Wake command: {wake_command}\n")
            self.queue.put(f"Scanning contract with Wake: {self.selected_contract}\n")
            self.run_command(wake_command)
        else:
            self.queue.put("No contract selected for Wake scan.\n")

    def scan_with_aderyn(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            # Step 1: Copy the contract
            contract_name = os.path.basename(self.selected_contract).split('.')[0]
            source_file = self.selected_contract
            destination_folder = "/home/robotics345/Aderyn/aderyn-contracts-playground/src"
            destination_file = os.path.join(destination_folder, f"{contract_name}.sol")
            
            copy_command = f"cp {source_file} {destination_file}"
            self.queue.put(f"Executing copy command: {copy_command}\n")
            
            try:
                result = subprocess.run(
                    copy_command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                self.queue.put(result.stdout)
            except subprocess.CalledProcessError as e:
                self.queue.put(f"Copy command failed with exit code {e.returncode}\n")
                self.queue.put(f"Error: {e.output}")
                return
            
            # Step 2: Change to the destination folder
            change_dir_command = "/home/robotics345/Aderyn/aderyn-contracts-playground"
            self.queue.put(f"Executing change directory command: {change_dir_command}\n")
            
            try:
                os.chdir(change_dir_command)
                current_dir = os.getcwd()
                self.queue.put(f"Current working directory changed to: {current_dir}\n")
            except Exception as e:
                self.queue.put(f"Failed to change directory: {str(e)}\n")
                return
            
            # Verify current directory
            current_dir = os.getcwd()
            self.queue.put(f"Verified current working directory: {current_dir}\n")
            
            # Step 3: Run Aderyn command
            aderyn_command = f"aderyn"
            self.queue.put(f"Running Aderyn: {aderyn_command}\n")
            
            try:
                result = subprocess.run(
                    aderyn_command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                self.queue.put(result.stdout)
            except subprocess.CalledProcessError as e:
                self.queue.put(f"Command failed with exit code {e.returncode}\n")
                self.queue.put(f"Error: {e.output}")
        else:
            self.queue.put("No contract selected for Aderyn scan.\n")

    def open_forge_setup_helper(self):
        self.forge_helper_window = tk.Toplevel(self)
        self.forge_helper_window.title("Forge Setup Helper")
        self.forge_helper_window.geometry("800x600")

        self.create_custom_terminal()

        # Update the custom terminal after creating it
        self.update_custom_output("Forge Setup Helper initialized.\n")

        # Keep the main window responsive
        self.after(100, lambda: self.forge_helper_window.grab_set())

        # Update the Forge Setup Helper window
        self.forge_helper_window.update_idletasks()


  
    def run_forge_test(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            # Use the stored contract_name instead of re-calculating it
            contract_name = self.contract_name

            # Step 1: Copy the contract
            source_file = self.selected_contract
            destination_folder = "/home/robotics345/Forgemeetscanner/src"
            destination_file = os.path.join(destination_folder, f"{contract_name}.sol")

            copy_command = f"cp {source_file} {destination_file}"
            self.queue.put(f"Executing copy command: {copy_command}\n")
            
            try:
                result = subprocess.run(
                    copy_command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                self.queue.put(result.stdout)
            except subprocess.CalledProcessError as e:
                self.queue.put(f"Copy command failed with exit code {e.returncode}\n")
                self.queue.put(f"Error: {e.output}")
                return

            # Step 2: Change directory to /home/robotics345/Forgemeetscanner/test
            change_dir_command = f"cd /home/robotics345/Forgemeetscanner/test"
            self.queue.put(f"Executing change directory command: {change_dir_command}\n")

            try:
                os.chdir("/home/robotics345/Forgemeetscanner/test")
                current_dir = os.getcwd()
                self.queue.put(f"Current working directory changed to: {current_dir}\n")
            except Exception as e:
                self.queue.put(f"Failed to change directory: {str(e)}\n")
                return

            # Step 3: Create a simple test file
            test_content = self.generate_test_file_content(contract_name)
            with open(f"{contract_name}.t.sol", "w") as f:
                f.write(test_content)

            self.queue.put(f"Created test file: {contract_name}.t.sol\n")
            
            # Step 4: Change directory to /home/robotics345/Forgemeetscanner/
            change_dir_command = f"cd /home/robotics345/Forgemeetscanner/"
            self.queue.put(f"Executing change directory command: {change_dir_command}\n")
            
            try:
                os.chdir("/home/robotics345/Forgemeetscanner/")
                current_dir = os.getcwd()
                self.queue.put(f"Current working directory changed to: {current_dir}\n")
            except Exception as e:
                self.queue.put(f"Failed to change directory: {str(e)}\n")
                return
            
            # Step 5: Run Forge test
            forge_command = f"forge test --contracts src/{contract_name}.sol"
            self.queue.put(f"Running Forge test: {forge_command}\n")
            
            try:
                result = subprocess.run(
                    forge_command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                self.queue.put(result.stdout)
            except subprocess.CalledProcessError as e:
                self.queue.put(f"Forge test command failed with exit code {e.returncode}\n")
                self.queue.put(f"Error: {e.output}")
            
        else:
            self.queue.put("No contract selected for Forge test.\n")

    def change_directory(self):
        def change_dir():
            directory = filedialog.askdirectory()
            if directory:
                os.chdir(directory)
                self.update_custom_output(f"Changed directory to: {directory}\n")
                popup.destroy()

        popup = tk.Toplevel(self.forge_helper_window)
        popup.title("Change Directory")

        label = tk.Label(popup, text="Select a directory:")
        label.pack(pady=10)

        button = tk.Button(popup, text="Browse Directory", command=change_dir)
        button.pack(pady=10)

        popup.grab_set()  # Make the popup modal
        popup.wait_window()  # Wait for the popup to be closed

    def create_test_file(self):
        if hasattr(self, 'selected_contract'):
            contract_name = os.path.basename(self.selected_contract).split('.')[0]
            test_content = self.generate_test_file_content(contract_name)
            with open(f"{contract_name}.t.sol", "w") as f:
                f.write(test_content)
            self.queue.put(f"Created test file: {contract_name}.t.sol\n")
        else:
            self.queue.put("No contract selected for creating test file.\n")

    def run_forge_build(self):
        command = "forge build"
        self.run_command(command)

    def run_forge_test(self):
        command = "forge test"
        self.run_command(command)

    def run_forge_install(self):
        command = "forge install"
        self.run_command(command)

    def run_git_init(self):
        command = "git init"
        self.run_command(command)

    def run_forge_openzeppelin_install(self):
        command = "forge install openzeppelin/openzeppelin-contracts@v4.8.3 --no-commit"
        self.run_command(command)

    def forge_init_new_project(self):
        def init_project():
            project_name = entry.get()
            if project_name:
                self.project_name = project_name
            
                command = f"forge init {project_name}"
                self.run_command(command)
            
                popup.destroy()

        popup = tk.Toplevel(self.forge_helper_window)
        popup.title("Enter Project Name")

        label = tk.Label(popup, text="Enter the name for your new project:")
        label.pack(pady=10)

        entry = tk.Entry(popup, width=30)
        entry.pack(pady=10)

        button = tk.Button(popup, text="Init New Project", command=init_project)
        button.pack(pady=10)

        popup.grab_set()  # Make the popup modal
        popup.wait_window()  # Wait for the popup to be closed

if __name__ == "__main__":
    app = Application()
    app.mainloop()

