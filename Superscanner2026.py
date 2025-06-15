import sys
import os
import subprocess
from PyQt5.QtCore import QProcess
import threading
import tempfile
import shutil
import requests
import ast
import re
from queue import Queue
from PyQt5.QtCore import QTimer
# Import QFont for font control
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QTextEdit, QFileDialog, QLabel, QSpacerItem, QSizePolicy, QInputDialog
import shlex
# Import html for escaping text for safe display
import html


class Application(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Contract Vulnerability Scanner")
        self.setGeometry(100, 100, 800, 1050)

        # Build paths dynamically from the user's home directory
        self.home_dir = os.path.expanduser('~')
        self.superscanner_dir = os.path.join(self.home_dir, 'Superscanner')
        self.aderyn_playground_dir = os.path.join(self.home_dir, 'aderyn-contracts-playground')
        self.foundry_installation_dir = os.path.join(self.home_dir, 'foundry_installation')


        # Version list for Solidity version selection
        self.version_list = [f"0.{i}.{j}" for i in range(
            4, 9) for j in range(0, 29)]
        self.version_var = QComboBox(self)
        self.version_var.addItems(self.version_list)
        self.version_var.setCurrentIndex(0)
        self.queue = Queue()

        # Title Labels for Static and Dynamic Scanners
        self.static_title = QLabel("Static Scanners")
        self.static_title.setStyleSheet("font-weight: bold;")
        self.dynamic_title = QLabel("Dynamic Scanners")
        self.dynamic_title.setStyleSheet("font-weight: bold;")

        # Left button layout (existing)
        self.button_layout = QVBoxLayout()
        self.button_layout.addWidget(self.version_var)

        self.change_button = QPushButton("Change Solc Version")
        self.change_button.clicked.connect(self.change_solc_version)
        self.button_layout.addWidget(self.change_button)

        self.select_button = QPushButton("Select Contract")
        self.select_button.clicked.connect(self.select_contract)
        self.button_layout.addWidget(self.select_button)

        self.button_layout.addWidget(self.static_title)

        self.scan_slither_button = QPushButton("Scan with Slither")
        self.scan_slither_button.clicked.connect(self.scan_contract_slither)
        self.button_layout.addWidget(self.scan_slither_button)

        self.scan_mythril_button = QPushButton("Scan with Mythril")
        self.scan_mythril_button.clicked.connect(self.scan_contract_mythril)
        self.button_layout.addWidget(self.scan_mythril_button)

        self.scan_solcscan_button = QPushButton("Scan with Solcscan")
        self.scan_solcscan_button.clicked.connect(self.scan_with_solcscan)
        self.button_layout.addWidget(self.scan_solcscan_button)

        self.falcon_scan_button = QPushButton("Scan with Falcon")
        self.falcon_scan_button.clicked.connect(self.scan_falcon)
        self.button_layout.addWidget(self.falcon_scan_button)

        self.wake_scan_button = QPushButton("Scan with Wake")
        self.wake_scan_button.clicked.connect(self.scan_with_wake)
        self.button_layout.addWidget(self.wake_scan_button)

        self.button_layout.addWidget(self.dynamic_title)

        self.scan_aderyn_button = QPushButton("Scan with Aderyn")
        self.scan_aderyn_button.clicked.connect(self.scan_with_aderyn)
        self.button_layout.addWidget(self.scan_aderyn_button)

        # Add ".sol Downloader" button
        self.sol_downloader_button = QPushButton(".sol Downloader")
        self.sol_downloader_button.clicked.connect(self.download_sol_file)
        self.button_layout.addWidget(self.sol_downloader_button)

        # Right button layout (Forge Playground)
        self.right_button_layout = QVBoxLayout()

        # Title for Forge Playground
        self.forge_title = QLabel("Forge Playground General Commands")
        self.forge_title.setStyleSheet("font-weight: bold;")
        self.right_button_layout.addWidget(self.forge_title)

        # Create buttons for each Forge command
        self.forge_clone_button = QPushButton("Forge Clone")
        self.forge_clone_button.clicked.connect(self.forge_clone)
        self.right_button_layout.addWidget(self.forge_clone_button)

        # Add the Forge Setup button
        self.forge_setup_button = QPushButton("Forge Setup")
        self.forge_setup_button.clicked.connect(self.forge_setup)
        self.right_button_layout.addWidget(self.forge_setup_button)

        # Add a button to copy the command "wake detect all"
        self.copy_command_button = QPushButton("Copy Command: wake detect all")
        self.copy_command_button.clicked.connect(
            lambda: self.copy_to_clipboard("wake detect all"))
        self.right_button_layout.addWidget(self.copy_command_button)

        # Add a spacer between the left and right layouts
        main_layout = QHBoxLayout(self)
        main_layout.addLayout(self.button_layout)
        main_layout.addSpacerItem(QSpacerItem(
            40, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(self.right_button_layout)

        # Create a vertical layout for command input and run button
        command_layout = QVBoxLayout()

        # Add command input area
        self.command_input = QTextEdit(self)
        # Set fixed size to match two buttons
        self.command_input.setFixedSize(200, 50)
        command_layout.addWidget(self.command_input)

        # Add "Run Code" button
        self.run_code_button = QPushButton("Run Code")
        self.run_code_button.clicked.connect(self.run_code)
        command_layout.addWidget(self.run_code_button)

        # Add the command layout to the right button layout under Forge Playground
        self.right_button_layout.addLayout(command_layout)

        # Output text area
        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(True)
        # Set a monospace font to preserve formatting of CLI tools
        self.output_text.setFont(QFont("monospace"))
        main_layout.addWidget(self.output_text)

        self.setLayout(main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_output)
        self.timer.start(100)

    def run_code(self):
        command = self.command_input.toPlainText()
        if command:
            self.run_command(command)

    def download_sol_file(self):
        """
        Downloads the Solidity file using the SourcifyMultichaindownloader script.
        """
        script_path = os.path.join(self.superscanner_dir, 'SourcifyMultichaindownloader.py')

        if not os.path.exists(script_path):
            self.queue.put(f"<span style='color: red;'>Error: Downloader script not found at {script_path}</span>")
            return

        # Create a QProcess to run the Sourcify downloader script
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments([script_path])

        # Set the working directory to where the script is located
        process.setWorkingDirectory(self.superscanner_dir)

        # Connect signals to handle output and errors
        process.readyReadStandardOutput.connect(
            lambda: self.handle_output(process))
        process.readyReadStandardError.connect(
            lambda: self.handle_error(process))
        process.finished.connect(
            lambda exitCode, exitStatus: self.handle_finish(exitCode, exitStatus))

        # Start the process
        process.start()

    def handle_output(self, process):
        output = process.readAllStandardOutput().data().decode()
        self.queue.put(f"<span style='color: green;'>{output}</span>")

    def handle_error(self, process):
        error = process.readAllStandardError().data().decode()
        self.queue.put(f"<span style='color: red;'>{error}</span>")

    def handle_finish(self, exitCode, exitStatus):
        if exitCode == 0:
            self.queue.put("Download completed successfully.\n")
        else:
            self.queue.put("Error occurred while downloading.\n")

    def extract_contract_name(self, text):
        match = re.search(r'contract\s+(\w+)', text)
        return match.group(1) if match else None

    def update_output(self):
        try:
            while True:
                text = self.queue.get_nowait()
                self.output_text.append(text)
        except:
            pass

    def clear_output(self):
        self.output_text.clear()

    def change_solc_version(self):
        self.clear_output()
        version = self.version_var.currentText()
        command = f"solc-select use {version}"
        self.run_command(command)

    def select_contract(self):
        self.clear_output()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Contract", "", "Solidity files (*.sol)")
        if filename:
            self.selected_contract = filename
            with open(filename, 'r') as file:
                contract_code = file.read()
                match = re.search(
                    r"pragma solidity (\^?[\d\.]+);", contract_code)
                if match:
                    solc_version = match.group(1).lstrip('^')
                    self.queue.put(
                        f"Detected Solidity version: {solc_version}\n")
                    version_string = self.format_version_for_solc(solc_version)
                    if version_string in self.version_list:
                        index = self.version_list.index(version_string)
                        self.version_var.setCurrentIndex(index)
                        self.run_command(f"solc-select use {version_string}")
                    else:
                        self.queue.put(
                            f"Version {version_string} is not available in the list.\n")
                else:
                    self.queue.put(
                        "Solidity version not found in the contract file.\n")
        else:
            self.queue.put("No contract selected.\n")

    def format_version_for_solc(self, version):
        parts = version.split('.')
        if len(parts) == 2:
            return f"0.{parts[0]}.{parts[1]}"
        elif len(parts) == 3:
            return version
        return version

    def forge_clone(self):
        self.clear_output()
        address, ok = QInputDialog.getText(
            self, "Enter Contract Address", "Enter the contract address to clone:")
        if ok and address:
            api_key = "YOUR_API_KEY"  # Replace with your actual API key
            temp_dir = tempfile.mkdtemp()

            try:
                self.run_command(
                    f"git config --global user.name 'lockmeilluminati'")
                self.run_command(
                    f"git config --global user.email 'lockme.illuminati@gmail.com'")
                self.run_command(f"git init {temp_dir}")
                self.run_command(f"forge init --force {temp_dir}")
                self.run_command(
                    f"forge clone {address} --etherscan-api-key {api_key} {temp_dir}")
                self.queue.put(
                    f"Contract successfully cloned into: {temp_dir}\n")
            except Exception as e:
                self.queue.put(f"Error: {str(e)}\n")
            shutil.rmtree(temp_dir)
        else:
            self.queue.put("No contract address provided.\n")

    def forge_setup(self):
        self.clear_output()

        if hasattr(self, 'selected_contract'):  # Ensure a contract is selected
            # Extract the contract name from the selected contract file
            contract_name = os.path.splitext(
                os.path.basename(self.selected_contract))[0]
            contract_file = f"{contract_name}.sol"

            new_directory = os.path.join(os.getcwd(), contract_name)

            if not os.path.exists(new_directory):
                os.makedirs(new_directory)
                self.queue.put(f"Created project directory: {new_directory}\n")
            else:
                self.queue.put(
                    f"Directory {new_directory} already exists. Aborting setup.\n")
                return

            # This is one of the few safe places to use os.chdir, as it's not in a thread
            # and we are setting up a project scaffold in the user's current directory.
            os.chdir(new_directory)

            self.run_command("forge init --no-commit")

            # Move the selected contract to the new Forge project
            contract_source_path = self.selected_contract
            contract_dest_path = os.path.join(
                new_directory, "src", contract_file)

            try:
                shutil.move(contract_source_path, contract_dest_path)
                self.queue.put(
                    f"Contract {contract_file} moved to {os.path.join('src', contract_file)}\n")
            except FileNotFoundError:
                self.queue.put(
                    f"Contract file {contract_file} not found in the original directory\n")
            except Exception as e:
                self.queue.put(f"Error moving contract file: {e}\n")
                return

            # Create the test file in the test directory
            solc_version = self.version_var.currentText()  # Get the selected version
            test_file_content = f"""// SPDX-License-Identifier: MIT
pragma solidity ^{solc_version};

import "forge-std/Test.sol";
import "../src/{contract_name}.sol";

contract {contract_name}Test is Test {{
    {contract_name} public contractInstance;

    function setUp() public {{
        contractInstance = new {contract_name}();
    }}
}}
"""
            test_file_path = os.path.join(
                new_directory, "test", f"{contract_name}Test.sol")
            with open(test_file_path, "w") as test_file:
                test_file.write(test_file_content)
            self.queue.put(f"Test file created at {test_file_path}\n")

            self.queue.put("Forge project setup completed successfully.\n")
        else:
            self.queue.put("No contract selected. Aborting setup.\n")

    def scan_contract_slither(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            command = f"slither {self.selected_contract}"
            self.run_command(command)
        else:
            self.queue.put("No contract selected for scanning.\n")

    def scan_contract_mythril(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            command = f"myth analyze {self.selected_contract}"
            self.run_command(command)
        else:
            self.queue.put("No contract selected for scanning.\n")

    def scan_with_solcscan(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            command = f"solcscan scan {self.selected_contract}"
            self.run_command(command)
        else:
            self.queue.put("No contract selected for scanning.\n")

    def scan_falcon(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            command = f"falcon {self.selected_contract}"
            self.run_command(command)
        else:
            self.queue.put("No contract selected for scanning.\n")

    def scan_with_wake(self):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            # Get the directory containing the selected contract (e.g., .../project/src)
            contract_dir = os.path.dirname(self.selected_contract)
            
            # Assume the project root is the parent directory (e.g., .../project)
            # This allows Wake to find dependencies in the 'lib' folder.
            project_root = os.path.dirname(contract_dir)

            # Safety check: if the parent is the same, we're at the top of the filesystem.
            # In that case, just use the contract's directory.
            if project_root == contract_dir:
                project_root = contract_dir

            command = "wake detect all"
            
            # Run the command from the determined project root
            self.run_command(command, cwd=project_root)
        else:
            self.queue.put("No contract selected for scanning.\n")


    def scan_with_aderyn(self):
        self.clear_output()
        if not hasattr(self, 'selected_contract'):
            self.queue.put("No contract selected for scanning.\n")
            return
        
        # This directory is configured by the installer script
        run_dir = self.aderyn_playground_dir
        playground_src_dir = os.path.join(run_dir, 'src')
        if not os.path.isdir(playground_src_dir):
            self.queue.put(f"<span style='color: red;'>Error: Aderyn playground 'src' directory not found at {playground_src_dir}. Please run the installer script.</span>")
            return

        try:
            # Copy contract to aderyn-contracts-playground/src
            contract_name = os.path.basename(self.selected_contract)
            dest_path = os.path.join(playground_src_dir, contract_name)

            shutil.copy(self.selected_contract, dest_path)
            self.queue.put(f"Copied contract to: {dest_path}\n")
            
            # Run commands in the correct directory without changing the app's global CWD
            self.run_command("forge build", cwd=run_dir)
            self.run_command("aderyn", cwd=run_dir)

        except Exception as e:
            self.queue.put(f"<span style='color: red;'>An unexpected error occurred during Aderyn scan setup: {str(e)}</span>")


    def copy_to_clipboard(self, command):
        clipboard = QApplication.clipboard()
        clipboard.setText(command)

    def run_command(self, command, cwd=None):
        def target():
            if cwd:
                log_msg = f"<span style='color: blue;'>Executing: {command} in directory {cwd}</span><br>"
            else:
                log_msg = f"<span style='color: blue;'>Executing: {command}</span><br>"
            self.queue.put(log_msg)
            
            try:
                # Use shlex.split to handle commands with spaces and arguments correctly
                args = shlex.split(command)
                # Run the command in the specified directory (cwd) if provided
                # This is more stable than os.chdir in a threaded GUI app
                result = subprocess.run(
                    args, 
                    check=True, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, 
                    universal_newlines=True, 
                    cwd=cwd
                )
                # Escape the raw stdout to prevent HTML injection and wrap in <pre>
                escaped_stdout = html.escape(result.stdout)
                formatted_output = f"<pre>{escaped_stdout}</pre>"
                self.queue.put(formatted_output)

            except subprocess.CalledProcessError as e:
                # Escape the raw stderr to prevent HTML injection and wrap in <pre>
                escaped_stderr = html.escape(e.output)
                # Note: Wake uses non-zero exit codes for successful detections.
                # Exit code 3 means detections were found. We can treat it as success.
                if "wake" in command and e.returncode == 3:
                     self.queue.put(f"<span style='color: green;'>Wake scan complete. Detections found (exit code 3):</span><br><pre>{escaped_stderr}</pre>")
                else:
                     self.queue.put(f"<span style='color: red;'>Error (return code {e.returncode}):<br><pre>{escaped_stderr}</pre></span>")

            except FileNotFoundError:
                self.queue.put(f"<span style='color: red;'>Command not found: '{command.split()[0]}'. Ensure it's installed and in your PATH.</span><br>")
            except Exception as e:
                self.queue.put(f"<span style='color: red;'>An unexpected error occurred: {str(e)}</span>")


        threading.Thread(target=target, daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Application()
    window.show()
    sys.exit(app.exec_())
