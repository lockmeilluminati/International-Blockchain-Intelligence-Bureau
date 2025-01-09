# SuperScanner Setup Guide for Ubuntu

## 1. Docker Install<br>
install with Docker<br>
docker pull doctorgraphene/superscanner:latest<br>
docker run -e DISPLAY=unix$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix --privileged myrustapp<br>
instead of myrustapp at the end it may be the scanner name still trying to figure it out 












[![Video Title](https://img.youtube.com/vi/9y8zN0GBoOs/0.jpg)](https://youtu.be/9y8zN0GBoOs?feature=shared)
click for video
# SuperScanner Setup Guide for Ubuntu

## Table of Contents
1. Prerequisites
2. Installation Steps
3. Running the Scanner

## 1. Prerequisites
-Serious note , i made sure not to use virtual environments on purpose so each app runs globally from anywhere in the terminal .
- Ubuntu system
- Python 3 installed
- Terminal access
- pip3 command : sudo apt install python3-pip


## 2. Installation Steps

1. Once you download solcscan we will put the superscanner.py file in there and run it 

2. Download the SuperScanner.py file into this directory.

3. Open the terminal inside the Solscan folder.

4. Install required dependencies:

sudo apt install python3-tk<br>
sudo add-apt-repository ppa:ethereum/ethereum <br>
sudo apt-get update<br>
sudo apt-get install solc<br>
pip3 install solc-select<br>


5. Install specific Solidity compiler versions:

to get solc to run globally you need to do this :<br>

Open your home directory's .bashrc file in a text editor:<br>

nano ~/.bashrc<br>

Add the following line at the end of the file:<br>

export PATH="$HOME/.local/bin:$PATH"<br>

This adds the directory containing Python's executable scripts (which includes solc-select) to your PATH.<br>

Save the file and exit the editor (in nano, press Ctrl+X, then Y, then Enter).<br>

To apply the changes immediately without restarting your terminal, run:<br>

source ~/.bashrc<br>

Verify that solc-select is now accessible by running:<br>

solc-select --version<br>

If you still encounter issues, you can try adding the specific directory where solc-select is installed:




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

## we need to install forge :

mkdir foundry<br>
cd foundry<br>
curl -L https://foundry.paradigm.xyz | bash<br>
source ~/.bashrc <br>
foundryup<br>
update it by running<br> 
foundryup<br>
forge init<br> 
git clone https://github.com/Cyfrin/aderyn-contracts-playground.git
cd aderyn-contracts-playground
forge build

## 2. Install the Scanners 
## Slither<br>
python3 -m pip install slither-analyzer<br>

## mythril<br>
pip3 install mythril<br>

## Falcon<br>
git clone https://github.com/MetaTrustLabs/falcon-metatrust.git<br>
cd falcon-metatrust<br>
pip3 install -r requirements-dev.txt<br>
python setup.py install<br>
## wake<br>
pip3 install eth-wake<br>
## Solc Scan<br>
3.Solc Scan<br>
git clone https://github.com/riczardo/solscan<br>
pip install click<br>
pip install termcolor<br>
pip install pyfiglet<br>
## aderyn<br>
sudo apt install curl
curl -L https://raw.githubusercontent.com/Cyfrin/aderyn/dev/cyfrinup/install | bash
cyfrinup
cyfrinup
git clone https://github.com/Cyfrin/aderyn-contracts-playground.git
cd aderyn-contracts-playground
forge build
sudo apt install curl<br>
curl -L https://raw.githubusercontent.com/Cyfrin/aderyn/dev/cyfrinup/install | bash<br>
cyfrinup<br>
cyfrinup<br>
git clone https://github.com/Cyfrin/aderyn-contracts-playground.git<br>
cd aderyn-contracts-playground<br>
forge build<br>


## 3. Running the Scanner

To run the scanner:

1. Navigate back to the Solscan folder containing SuperScanner.py.

2. Run the following command:

python3 scannerbeta.py


Important notes:
- Ensure you're inside the correct directory when running the script.
- If any command fails, troubleshoot by running each step individually.
- For detailed installation instructions, refer to the official documentation links provided in the README.

## Troubleshooting

If you encounter issues during installation or execution, please consult the official GitHub repositories for each tool:
- Aderyn: https://github.com/Cyfrin/aderyn?tab=readme-ov-file
- Solscan: https://github.com/riczardo/solscan
- Slither: https://github.com/crytic/slither
- Mythril: https://github.com/Consensys/mythril
- Falcon: https://github.com/MetaTrustLabs/falcon-metatrust
- Wake: https://github.com/Ackee-Blockchain/wake

By following these steps, you should have a fully functional setup for running the SuperScanner.py on your Ubuntu system.

