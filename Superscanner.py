import sys
import os
import subprocess
import threading
import tempfile
import shutil
import requests
import ast
import re
from queue import Queue
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QTextEdit, QFileDialog, QLabel, QSpacerItem, QSizePolicy, QInputDialog


class Application(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Contract Vulnerability Scanner")
        self.setGeometry(100, 100, 800, 1050)

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

        # Add a spacer between the left and right layouts
        main_layout = QHBoxLayout(self)
        main_layout.addLayout(self.button_layout)
        main_layout.addSpacerItem(QSpacerItem(
            40, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(self.right_button_layout)

        # Output text area
        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)

        self.setLayout(main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_output)
        self.timer.start(100)

    def download_sol_file(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        contract_name = self.extract_contract_name(clipboard_text)
        file_name = f"{contract_name}.sol" if contract_name else "untitled.sol"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", file_name, "Solidity Files (*.sol);;All Files (*)"
        )

        if file_path:
            with open(file_path, 'w') as file:
                file.write(clipboard_text)
            self.queue.put(f"Contract saved as {file_path}\n")
        else:
            self.queue.put("Save operation canceled.\n")

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

            os.chdir(new_directory)

            try:
                subprocess.run(["forge", "init", "--no-commit"], check=True)
                self.queue.put(
                    f"Forge project initialized in {new_directory}\n")
            except subprocess.CalledProcessError as e:
                self.queue.put(f"Error during Forge initialization: {e}\n")
                return

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
                    f"Contract file {contract_file} not found in the current directory\n")
                return
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

    // Contract setup
    function setUp() public {{
        contractInstance = new {contract_name}();
    }}

    // Boundary values: Test minimum and maximum for uint256
    function testBoundaryValues(uint256 _input) public {{
        uint256 maxValue = type(uint256).max;
        uint256 underflowValue = maxValue - 1;

        // Test underflow value
        contractInstance.someFunction(underflowValue);

        // Test maximum value
        contractInstance.someFunction(maxValue);
    }}

    // Random Byte Strings: Test with random bytes input
    function testRandomBytes(bytes32 _input) public {{
        contractInstance.someFunction(_input);
    }}

    // Random Addresses: Test with random address input
    function testRandomAddresses(address _randomAddress) public {{
        contractInstance.someFunction(_randomAddress);
    }}

    // Random Ether Amounts: Test with random Ether amounts
    function testRandomEtherAmount(uint256 _amount) public payable {{
        // Ensure the amount is within a reasonable range
        require(_amount < address(this).balance, "Not enough balance");
        contractInstance.deposit{{value: _amount}}();
    }}

    // Random User-Generated Input for Function Calls
    function testRandomFunctionOrder(uint256 _value, address _address) public {{
        if (_value % 2 == 0) {{
            contractInstance.someFunctionA(_value);
        }} else {{
            contractInstance.someFunctionB(_address);
        }}
    }}

    // State Transitions and Unexpected Sequence: Test random state transitions
    function testStateTransition(uint256 _amount) public {{
        if (_amount % 2 == 0) {{
            contractInstance.deposit(_amount);
        }} else {{
            contractInstance.withdraw(_amount);
        }}
    }}

    // Random Sequence of Failures/Successes
    function testRandomSuccessFailures(uint256 _randomValue) public {{
        if (_randomValue % 2 == 0) {{
            contractInstance.successFunction();
        }} else {{
            try contractInstance.failFunction(_randomValue) {{
                // Expect failure, so handle it
            }} catch (bytes memory) {{
                assert(true);  // This should catch the expected failure
            }}
        }}
    }}

    // Random Storage Interactions: Test random writes and reads from storage
    function testRandomStorageInteraction(uint256 _index, uint256 _value) public {{
        contractInstance.setStorageValue(_index, _value);
        uint256 storedValue = contractInstance.getStorageValue(_index);
        assert(storedValue == _value);
    }}

    // Random Failures with Gas Limit Manipulation: Test with random gas limits
    function testRandomGasLimit(uint256 _gasLimit) public {{
        uint256 initialGas = gasleft();
        contractInstance.someFunction();
        uint256 usedGas = initialGas - gasleft();
        require(usedGas < _gasLimit, "Gas limit exceeded");
    }}

    // Test with random values using vm.assume() for further fuzzing
    function testRandom(uint256 _input) public {{
        // Assume we are testing with a random value
        vm.assume(_input != 0); // Prevents 0 from being tested as an edge case
        contractInstance.someFunction(_input);
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

    def run_scanner(self, scanner_cmd, venv_path):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            command = f"{venv_path}/bin/python {scanner_cmd} {self.selected_contract}"
            self.run_command(command)
        else:
            self.queue.put("No contract selected for scanning.\n")

    def scan_contract_slither(self):
        self.run_scanner("slither", "/home/robotics345/Venvs/slither_env")

    def scan_contract_mythril(self):
        self.run_scanner("myth analyze", "/home/robotics345/Venvs/mythril_env")

    def scan_with_solcscan(self):
        self.run_scanner("/home/robotics345/solscan/main.py scan",
                         "/home/robotics345/Venvs/solscan_env")

    def scan_falcon(self):
        self.run_scanner("falcon", "/home/robotics345/Venvs/falcon_env")

    def scan_with_wake(self):
        self.run_scanner("wake", "/home/robotics345/Venvs/wake_env")

    def scan_with_aderyn(self):
        self.run_scanner("aderyn", "/home/robotics345/Venvs/aderyn_env")

    def run_command(self, command):
        def target():
            self.queue.put(f"Executing: {command}\n")
            try:
                result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, universal_newlines=True)
                self.queue.put(result.stdout)
            except subprocess.CalledProcessError as e:
                self.queue.put(f"Error: {e.output}")

        threading.Thread(target=target, daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Application()
    window.show()
    sys.exit(app.exec_())
