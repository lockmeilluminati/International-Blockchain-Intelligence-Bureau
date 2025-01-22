import os
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QComboBox

# Function to download Solidity files and save them individually


def download_solidity_files(chain, address):
    # URL for the API request
    url = f'https://sourcify.dev/server/files/any/{chain}/{address}'

    # Send GET request to retrieve contract files
    response = requests.get(url, headers={'accept': 'application/json'})

    if response.status_code == 200:
        data = response.json()

        # Directory to save the Solidity files
        save_dir = f"{address}_sol_files"
        os.makedirs(save_dir, exist_ok=True)

        # Loop through each file in the response
        for file in data.get('files', []):
            file_name = file.get('name')
            file_content = file.get('content')

            # Define file path to save the file
            file_path = os.path.join(save_dir, file_name)

            # Save the file content as a .sol file
            with open(file_path, 'w') as sol_file:
                sol_file.write(file_content)
            print(f"Saved: {file_name} to {file_path}")

        return save_dir
    else:
        print(
            f"Failed to retrieve files for {address} on chain {chain}. Status code: {response.status_code}")
        return None

# PyQt5 application


class ContractDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Contract Downloader')
        self.setGeometry(300, 300, 500, 350)

        # Layout setup
        self.layout = QVBoxLayout()

        # Dropdown for chain selection
        self.chain_dropdown = QComboBox(self)
        # Chain ID 1 for Ethereum Mainnet
        self.chain_dropdown.addItem('Ethereum Mainnet', 1)
        # Chain ID 56 for Binance Smart Chain
        self.chain_dropdown.addItem('Binance Smart Chain', 56)
        self.chain_dropdown.addItem('Polygon', 137)  # Chain ID 137 for Polygon
        # Chain ID 43114 for Avalanche
        self.chain_dropdown.addItem('Avalanche', 43114)
        self.chain_dropdown.addItem('Fantom', 250)  # Chain ID 250 for Fantom
        self.chain_dropdown.addItem('Optimism', 10)  # Chain ID 10 for Optimism
        # Chain ID 42161 for Arbitrum
        self.chain_dropdown.addItem('Arbitrum', 42161)
        # Chain ID 5 for Goerli Testnet
        self.chain_dropdown.addItem('Goerli Testnet', 5)
        self.layout.addWidget(self.chain_dropdown)

        # Label for contract address input
        self.label_address = QLabel('Enter Contract Address:', self)
        self.layout.addWidget(self.label_address)

        # Input field for contract address
        self.contract_address_input = QLineEdit(self)
        self.layout.addWidget(self.contract_address_input)

        # Label for custom chain ID input
        self.label_chain_id = QLabel('Enter Custom Chain ID (optional):', self)
        self.layout.addWidget(self.label_chain_id)

        # Input field for custom chain ID
        self.custom_chain_id_input = QLineEdit(self)
        self.layout.addWidget(self.custom_chain_id_input)

        # Download button
        self.download_button = QPushButton('Download Solidity Files', self)
        self.download_button.clicked.connect(self.download_files)
        self.layout.addWidget(self.download_button)

        # Change Chain ID button
        self.change_chain_button = QPushButton('Change Chain ID', self)
        self.change_chain_button.clicked.connect(self.change_chain_id)
        self.layout.addWidget(self.change_chain_button)

        # Set the layout to the window
        self.setLayout(self.layout)

    def download_files(self):
        contract_address = self.contract_address_input.text()
        custom_chain_id = self.custom_chain_id_input.text()

        if contract_address:
            # If custom chain ID is provided, use it. Otherwise, use the selected chain from the dropdown.
            selected_chain_id = int(
                custom_chain_id) if custom_chain_id else self.chain_dropdown.currentData()

            # Only download the files without submitting
            files_dir = download_solidity_files(
                selected_chain_id, contract_address)

            if files_dir:
                QMessageBox.information(
                    self, "Success", f"Files downloaded successfully to {files_dir}.")
            else:
                QMessageBox.warning(
                    self, "Error", "Failed to download Solidity files.")
        else:
            QMessageBox.warning(
                self, "Error", "Please enter a valid contract address.")

    def change_chain_id(self):
        selected_chain_id = self.chain_dropdown.currentData()
        QMessageBox.information(self, "Chain ID Changed",
                                f"Current Chain ID: {selected_chain_id}")


# Create and run the PyQt application
app = QApplication([])
window = ContractDownloaderApp()
window.show()
app.exec_()
