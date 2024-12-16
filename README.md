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
solc-select install 0.4.0
solc-select install 0.4.1
solc-select install 0.4.2
solc-select install 0.4.3
solc-select install 0.4.4
solc-select install 0.4.5
solc-select install 0.4.6
solc-select install 0.4.7
solc-select install 0.4.8
solc-select install 0.4.9
solc-select install 0.4.10
solc-select install 0.4.11
solc-select install 0.4.12
solc-select install 0.4.13
solc-select install 0.4.14
solc-select install 0.4.15
solc-select install 0.4.16
solc-select install 0.4.17
solc-select install 0.4.18
solc-select install 0.4.19
solc-select install 0.4.20
solc-select install 0.4.21
solc-select install 0.4.22
solc-select install 0.4.23
solc-select install 0.4.24
solc-select install 0.4.25
solc-select install 0.4.26
solc-select install 0.5.0
solc-select install 0.5.1
solc-select install 0.5.2
solc-select install 0.5.3
solc-select install 0.5.4
solc-select install 0.5.5
solc-select install 0.5.6
solc-select install 0.5.7
solc-select install 0.5.8
solc-select install 0.5.9
solc-select install 0.5.10
solc-select install 0.5.11
solc-select install 0.5.12
solc-select install 0.5.13
solc-select install 0.5.14
solc-select install 0.5.15
solc-select install 0.6.0
solc-select install 0.6.1
solc-select install 0.6.2
solc-select install 0.6.3
solc-select install 0.6.4
solc-select install 0.6.5
solc-select install 0.6.6
solc-select install 0.6.7
solc-select install 0.6.8
solc-select install 0.6.9
solc-select install 0.6.10
solc-select install 0.6.11
solc-select install 0.6.12
solc-select install 0.7.0
solc-select install 0.7.1
solc-select install 0.7.2
solc-select install 0.7.3
solc-select install 0.7.4
solc-select install 0.7.5
solc-select install 0.7.6
solc-select install 0.8.0
solc-select install 0.8.1
solc-select install 0.8.2
solc-select install 0.8.3
solc-select install 0.8.4
solc-select install 0.8.5
solc-select install 0.8.6
solc-select install 0.8.7
solc-select install 0.8.8
solc-select install 0.8.9
solc-select install 0.8.10
solc-select install 0.8.11
solc-select install 0.8.12
solc-select install 0.8.13
solc-select install 0.8.14
solc-select install 0.8.15
solc-select install 0.8.16
solc-select install 0.8.17
solc-select install 0.8.18
solc-select install 0.8.19
solc-select install 0.8.20
solc-select install 0.8.21
solc-select install 0.8.22
solc-select install 0.8.23
solc-select install 0.8.24
solc-select install 0.8.25
solc-select install 0.8.26
solc-select install 0.8.27
solc-select install 0.8.28



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


