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

sudo apt install python3-tk<br>
sudo add-apt-repository ppa:ethereum/ethereum <br>
sudo apt-get update<br>
sudo apt-get install solc<br>
pip3 install solc-select<br>


5. Install specific Solidity compiler versions:
solc-select install 0.4.0<br>
solc-select install 0.4.1<br>
solc-select install 0.4.2<br>
solc-select install 0.4.3<br>
solc-select install 0.4.4<br>
solc-select install 0.4.5<br>
solc-select install 0.4.6<br>
solc-select install 0.4.7<br>
solc-select install 0.4.8<br>
solc-select install 0.4.9<br>
solc-select install 0.4.10<br>
solc-select install 0.4.11<br>
solc-select install 0.4.12<br>
solc-select install 0.4.13<br>
solc-select install 0.4.14<br>
solc-select install 0.4.15<br>
solc-select install 0.4.16<br>
solc-select install 0.4.17<br>
solc-select install 0.4.18<br>
solc-select install 0.4.19<br>
solc-select install 0.4.20<br>
solc-select install 0.4.21<br>
solc-select install 0.4.22<br>
solc-select install 0.4.23<br>
solc-select install 0.4.24<br>
solc-select install 0.4.25<br>
solc-select install 0.4.26<br>
solc-select install 0.5.0<br>
solc-select install 0.5.1<br>
solc-select install 0.5.2<br>
solc-select install 0.5.3<br>
solc-select install 0.5.4<br>
solc-select install 0.5.5<br>
solc-select install 0.5.6<br>
solc-select install 0.5.7<br>
solc-select install 0.5.8<br>
solc-select install 0.5.9<br>
solc-select install 0.5.10<br>
solc-select install 0.5.11<br>
solc-select install 0.5.12<br>
solc-select install 0.5.13<br>
solc-select install 0.5.14<br>
solc-select install 0.5.15<br>
solc-select install 0.6.0<br>
solc-select install 0.6.1<br>
solc-select install 0.6.2<br>
solc-select install 0.6.3<br>
solc-select install 0.6.4<br>
solc-select install 0.6.5<br>
solc-select install 0.6.6<br>
solc-select install 0.6.7<br>
solc-select install 0.6.8<br>
solc-select install 0.6.9<br>
solc-select install 0.6.10<br>
solc-select install 0.6.11<br>
solc-select install 0.6.12<br>
solc-select install 0.7.0<br>
solc-select install 0.7.1<br>
solc-select install 0.7.2<br>
solc-select install 0.7.3<br>
solc-select install 0.7.4<br>
solc-select install 0.7.5<br>
solc-select install 0.7.6<br>
solc-select install 0.8.0<br>
solc-select install 0.8.1<br>
solc-select install 0.8.2<br>
solc-select install 0.8.3<br>
solc-select install 0.8.4<br>
solc-select install 0.8.5<br>
solc-select install 0.8.6<br>
solc-select install 0.8.7<br>
solc-select install 0.8.8<br>
solc-select install 0.8.9<br>
solc-select install 0.8.10<br>
solc-select install 0.8.11<br>
solc-select install 0.8.12<br>
solc-select install 0.8.13<br>
solc-select install 0.8.14<br>
solc-select install 0.8.15<br>
solc-select install 0.8.16<br>
solc-select install 0.8.17<br>
solc-select install 0.8.18<br>
solc-select install 0.8.19<br>
solc-select install 0.8.20<br>
solc-select install 0.8.21<br>
solc-select install 0.8.22<br>
solc-select install 0.8.23<br>
solc-select install 0.8.24<br>
solc-select install 0.8.25<br>
solc-select install 0.8.26<br>
solc-select install 0.8.27<br>
solc-select install 0.8.28<br>




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


