# SuperScanner Setup Guide for Ubuntu

## Table of Contents
1. Prerequisites
2. Installation Steps
3. Running the Scanner

## 1. Prerequisites

- Ubuntu system
- Python 3 installed
- Terminal access

## 2. Installation Steps

1. Create a new directory for the project:

mkdir Solscan cd Solscan


2. Download the SuperScanner.py file into this directory.

3. Open the terminal inside the Solscan folder.

4. Install required dependencies:

sudo apt install python3-tk python3-pip sudo add-apt-repository ppa:ethereum/ethereum sudo apt-get update sudo apt-get install solc pip3 install solc-select


5. Install specific Solidity compiler versions:

solc-select install 0.4.0 solc-select install 0.4.1 ... solc-select install 0.8.28


6. Install additional tools:

pip3 install slither mythril falcon wake git clone https://github.com/riczardo/solscan cd solscan pip install click termcolor pyfiglet


## 3. Running the Scanner

To run the scanner:

1. Navigate back to the Solscan folder containing SuperScanner.py.

2. Run the following command:

python3 SuperScanner.py


Important notes:
- Ensure you're inside the correct directory when running the script.
- If any command fails, troubleshoot by running each step individually.
- For detailed installation instructions, refer to the official documentation links provided in the README.

## Troubleshooting

If you encounter issues during installation or execution, please consult the official GitHub repositories for each tool:

- Solscan: https://github.com/riczardo/solscan
- Slither: https://github.com/crytic/slither
- Mythril: https://github.com/Consensys/mythril
- Falcon: https://github.com/MetaTrustLabs/falcon-metatrust
- Wake: https://github.com/Ackee-Blockchain/wake

By following these steps, you should have a fully functional setup for running the SuperScanner.py on your Ubuntu system.


