#!/usr/bin/env python3

import os
import subprocess
import platform

# --- Configuration ---
# The home directory for path expansion.
HOME_DIR = os.path.expanduser('~')
# The central directory to hold all scanner virtual environments.
VENV_PARENT_DIR = os.path.join(HOME_DIR, 'scanner_venvs')
# The directory for global symbolic links.
GLOBAL_BIN_DIR = os.path.join(HOME_DIR, '.local/bin')


# These steps are updated to create isolated virtual environments for each scanner.
INSTALLATION_STEPS = [
    {
        "title": "Install Prerequisites (pip, tk, git, curl, venv)",
        "commands": [
            "sudo apt update",
            "sudo apt install -y python3-pip python3-tk git curl python3-venv",
        ],
        "info": "Installs pip, tkinter, git, curl, and the 'venv' module for creating virtual environments."
    },
    {
        "title": "Install Ethereum Tooling (solc & solc-select)",
        "commands": [
            "sudo add-apt-repository ppa:ethereum/ethereum -y",
            "sudo apt-get update",
            "sudo apt-get install solc -y",
            "pip3 install solc-select",
        ],
        "info": "Adds the Ethereum PPA to install the Solidity compiler and its version manager."
    },
    {
        "title": "Configure Environment PATH for Global Tools",
        "commands": [
            f"mkdir -p {GLOBAL_BIN_DIR}",
            f"echo 'export PATH=\"{GLOBAL_BIN_DIR}:$PATH\"' >> {HOME_DIR}/.bashrc",
            f"echo 'export PATH=\"{HOME_DIR}/.cargo/bin:$PATH\"' >> {HOME_DIR}/.bashrc",
            f"source {HOME_DIR}/.bashrc",
        ],
        "info": "Ensures the directory for global tools exists and adds it (and Cargo's bin) to the system PATH."
    },
    {
        "title": "Install Foundry Toolkit",
        "commands": [
            "rm -rf foundry_installation && mkdir foundry_installation",
            (
                "cd foundry_installation && "
                "curl -L https://foundry.paradigm.xyz | bash && "
                f"source {HOME_DIR}/.bashrc && "
                "foundryup && "
                "foundryup && "
                "forge init --force && "
                "cd .."
            )
        ],
        "info": "Installs the Foundry toolkit in its own directory using your specific command sequence."
    },
    {
        "title": "Install Aderyn",
        "commands": [
            "curl --proto '=https' --tlsv1.2 -LsSf https://github.com/cyfrin/aderyn/releases/latest/download/aderyn-installer.sh | bash",
        ],
        "info": "Installs Aderyn using the official installer. This modifies your PATH, which the next step will use."
    },
    {
        "title": "Initialize and Update Aderyn",
        "commands": [
            f"source {HOME_DIR}/.bashrc && aderyn",
            f"source {HOME_DIR}/.bashrc && aderyn-update"
        ],
        "info": "Runs Aderyn to initialize it and then updates it. The 'source' command is required for the script to find 'aderyn' right after installation."
    },
    {
        "title": "Create Directory for Other Scanner Venvs",
        "commands": [
            f"mkdir -p {VENV_PARENT_DIR}",
            f"echo 'Created main directory for virtual environments at: {VENV_PARENT_DIR}'"
        ],
        "info": "A central folder will be created to hold all the other isolated scanner environments."
    },
    {
        "title": "Install Slither (in Virtual Environment)",
        "commands": [
            f"python3 -m venv {VENV_PARENT_DIR}/slither_env",
            f"{VENV_PARENT_DIR}/slither_env/bin/pip install slither-analyzer",
            f"sudo ln -sf {VENV_PARENT_DIR}/slither_env/bin/slither {GLOBAL_BIN_DIR}/slither",
            f"echo 'Slither installed in: {VENV_PARENT_DIR}/slither_env and linked globally.'"
        ],
        "info": "Creates a dedicated virtual environment for Slither and links its executable for global access."
    },
    {
        "title": "Install Mythril (in Virtual Environment)",
        "commands": [
            f"python3 -m venv {VENV_PARENT_DIR}/mythril_env",
            f"{VENV_PARENT_DIR}/mythril_env/bin/pip install mythril",
            f"sudo ln -sf {VENV_PARENT_DIR}/mythril_env/bin/myth {GLOBAL_BIN_DIR}/myth",
            f"echo 'Mythril installed in: {VENV_PARENT_DIR}/mythril_env and linked globally.'"
        ],
        "info": "Creates a dedicated virtual environment for Mythril and links its executable for global access."
    },
    {
        "title": "Install eth-wake (in Virtual Environment)",
        "commands": [
            f"python3 -m venv {VENV_PARENT_DIR}/wake_env",
            f"{VENV_PARENT_DIR}/wake_env/bin/pip install eth-wake",
            f"sudo ln -sf {VENV_PARENT_DIR}/wake_env/bin/wake {GLOBAL_BIN_DIR}/wake",
            f"echo 'eth-wake installed in: {VENV_PARENT_DIR}/wake_env and linked globally.'"
        ],
        "info": "Creates a dedicated virtual environment for eth-wake and links its executable for global access."
    },
    {
        "title": "Install Falcon (in Virtual Environment)",
        "commands": [
            "rm -rf falcon-metatrust && git clone https://github.com/MetaTrustLabs/falcon-metatrust.git",
            f"python3 -m venv {VENV_PARENT_DIR}/falcon_env",
            f"{VENV_PARENT_DIR}/falcon_env/bin/pip install -r falcon-metatrust/requirements-dev.txt",
            f"cd falcon-metatrust && {VENV_PARENT_DIR}/falcon_env/bin/python setup.py install && cd ..",
            f"sudo ln -sf {VENV_PARENT_DIR}/falcon_env/bin/falcon {GLOBAL_BIN_DIR}/falcon",
            f"echo 'Falcon installed in: {VENV_PARENT_DIR}/falcon_env and linked globally.'"
        ],
        "info": "Clones and installs the Falcon scanner into its own virtual environment and links it globally."
    },
    {
        "title": "Install Solc-Scan & Dependencies",
        "commands": [
            "rm -rf solscan && git clone https://github.com/riczardo/solscan.git",
            "pip3 install --target=./solscan click termcolor pyfiglet",
            f"""printf '#!/bin/bash\\npython3 $(pwd)/solscan/main.py "$@"\\n' | sudo tee {GLOBAL_BIN_DIR}/solcscan > /dev/null""",
            f"sudo chmod +x {GLOBAL_BIN_DIR}/solcscan",
            "echo 'Solc-Scan and its dependencies installed in the ./solscan directory and linked globally.'"
        ],
        "info": "Clones Solc-Scan, installs dependencies into the tool's folder, and creates a global 'solcscan' command."
    },
    {
        "title": "Install All Solidity Compiler Versions",
        "commands": [
            f"source {HOME_DIR}/.bashrc && solc-select install all",
        ],
        "info": "This will download all available Solidity versions. It can take a significant amount of time."
    }
]

# --- Colors for Terminal Output ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- Main Application Logic ---
def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    """Prints the main menu of installation steps."""
    clear_screen()
    print(f"{Colors.HEADER}{Colors.BOLD}SuperScanner Installer (with Virtual Environments){Colors.ENDC}")
    print(f"{Colors.HEADER}--------------------------------------------------{Colors.ENDC}")
    print("Select a step to run:")
    for i, step in enumerate(INSTALLATION_STEPS, 1):
        print(f"  {Colors.YELLOW}{i}{Colors.ENDC}. {step['title']}")
    print(f"  {Colors.YELLOW}all{Colors.ENDC}. Run all steps from top to bottom")
    print(f"  {Colors.YELLOW}q{Colors.ENDC}. Quit")
    print(f"{Colors.HEADER}--------------------------------------------------{Colors.ENDC}")

def execute_commands(step):
    """Executes the commands for a given installation step."""
    title = step.get('title', 'Untitled Step')
    commands = step.get('commands', [])
    info = step.get('info', '')

    print(f"\n{Colors.BLUE}--- Running Step: {title} ---{Colors.ENDC}\n")
    if info:
        print(f"{Colors.YELLOW}INFO: {info}{Colors.ENDC}\n")

    if input("Press Enter to continue, or type 's' to skip: ").lower() == 's':
        print(f"{Colors.YELLOW}Skipping step.{Colors.ENDC}")
        return True

    for command in commands:
        print(f"\n{Colors.BOLD}Executing: {command}{Colors.ENDC}")
        try:
            process = subprocess.run(
                command,
                shell=True,
                check=True,
                executable='/bin/bash',
                capture_output=True,
                text=True
            )
            if process.stdout:
                print(process.stdout)
            if process.stderr:
                print(f"{Colors.YELLOW}{process.stderr}{Colors.ENDC}")
            print(f"{Colors.GREEN}Successfully executed: {command}{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}Error executing command: {command}{Colors.ENDC}")
            print(f"{Colors.RED}Return code: {e.returncode}{Colors.ENDC}")
            print(f"{Colors.RED}--- STDOUT ---\n{e.stdout}{Colors.ENDC}")
            print(f"{Colors.RED}--- STDERR ---\n{e.stderr}{Colors.ENDC}")
            if input("Do you want to continue with the next command? (y/n): ").lower() != 'y':
                print(f"{Colors.RED}Aborting step.{Colors.ENDC}")
                return False
    print(f"\n{Colors.GREEN}--- Finished Step: {title} ---{Colors.ENDC}")
    return True

def run_all_steps():
    """Executes all installation steps in sequence."""
    clear_screen()
    print(f"{Colors.HEADER}{Colors.BOLD}--- Running All Installation Steps ---{Colors.ENDC}")
    for i, step in enumerate(INSTALLATION_STEPS, 1):
        if not execute_commands(step):
            print(f"{Colors.RED}Installation stopped due to an error in step {i}.{Colors.ENDC}")
            break
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All installation steps completed!{Colors.ENDC}")

def main():
    """Main function to run the interactive installer."""
    if platform.system() != "Linux":
        print(f"{Colors.RED}This script is designed for Debian-based Linux (like Ubuntu). Exiting.{Colors.ENDC}")
        return

    while True:
        print_menu()
        choice = input("Enter your choice: ").lower().strip()

        if choice in ('q', 'quit'):
            break

        if choice == 'all':
            run_all_steps()
            input("\nPress Enter to return to the menu.")
            continue

        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(INSTALLATION_STEPS):
                step = INSTALLATION_STEPS[choice_index]
                execute_commands(step)
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a number from the menu.{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number, 'all', or 'q'.{Colors.ENDC}")

        input("\nPress Enter to return to the menu.")

if __name__ == "__main__":
    main()

