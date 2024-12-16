import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import threading
from queue import Queue
import logging
import os

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

        self.scan_slither_button = tk.Button(self.button_frame, text="Scan with Slither", command=lambda: self.scan_contract("slither"))
        self.scan_slither_button.pack(side=tk.LEFT, padx=5)

        self.scan_mythril_button = tk.Button(self.button_frame, text="Scan with Mythril", command=lambda: self.scan_contract("mythril"))
        self.scan_mythril_button.pack(side=tk.LEFT, padx=5)

        self.scan_solcscan_button = tk.Button(self.button_frame, text="Scan with Solcscan", command=self.scan_with_solcscan)
        self.scan_solcscan_button.pack(side=tk.LEFT, padx=5)

        self.falcon_scan_button = tk.Button(self.button_frame, text="Scan with Falcon", command=self.scan_falcon)
        self.falcon_scan_button.pack(side=tk.LEFT, padx=5)

        self.wake_scan_button = tk.Button(self.button_frame, text="Scan with Wake", command=self.scan_with_wake)
        self.wake_scan_button.pack(side=tk.LEFT, padx=5)

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

    def select_contract(self):
        self.clear_output()
        filename = filedialog.askopenfilename(filetypes=[("Solidity files", "*.sol")])
        if filename:
            self.selected_contract = filename
            self.queue.put(f"Selected contract: {filename}\n")

    def scan_contract(self, tool):
        self.clear_output()
        if hasattr(self, 'selected_contract'):
            if tool == "slither":
                slither_command = f"slither {self.selected_contract}"
            elif tool == "mythril":
                mythril_command = f"myth analyze {self.selected_contract}"
            else:
                self.queue.put("Invalid tool selected.\n")
                return

            self.queue.put(f"Scanning contract with {tool}: {self.selected_contract}\n")
            self.run_command(slither_command if tool == "slither" else mythril_command)
        else:
            self.queue.put(f"No contract selected for {tool} scan.\n")

    def run_command(self, command):
        def target():
            self.queue.put(f"Executing command: {command}\n")
            try:
                result = subprocess.run(
                    command,
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

if __name__ == "__main__":
    app = Application()
    app.mainloop()

