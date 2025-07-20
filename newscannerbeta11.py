import sys
import os
import subprocess
import json
from PyQt5.QtCore import QDir, QPoint, Qt, QEvent, QTimer
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QTextEdit, QFileDialog, QLabel, QSpacerItem,
                             QSizePolicy, QInputDialog, QFormLayout, QGroupBox,
                             QTreeView, QFileSystemModel, QSplitter, QMenu,
                             QMessageBox, QLineEdit, QScrollArea, QGridLayout,
                             QTextBrowser, QDialog, QDialogButtonBox)

import shlex
import html
from queue import Queue
import threading
import re
import shutil
import toml
from datetime import datetime
import traceback
import tempfile

# Attempt to import Slither, provide guidance if not found.
try:
    from slither import Slither
    from slither.exceptions import SlitherError
except ImportError:
    print("Error: Py-Slither is not installed. Please run 'pip install slither-analyzer'.")
    Slither = None # Set to None to handle it gracefully

# Attempt to import exploit templates, handle gracefully if not found.
try:
    from exploit_db import EXPLOIT_TEMPLATES
except ImportError:
    print("Warning: exploit_db.py not found. Exploit generation will be limited.")
    EXPLOIT_TEMPLATES = {}

class Application(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aave Security Analysis & Monitoring Station")
        self.setGeometry(100, 100, 1920, 1080)

        # --- Styling ---
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'monospace'; }
            QGroupBox { font-weight: bold; border: 1px solid #4a4a4a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; background-color: #1e1e1e; }
            QPushButton { background-color: #3c3c3c; border: 1px solid #6c6c6c; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:pressed { background-color: #2a2a2a; }
            QPushButton#overrideButton { background-color: #5a3d5c; }
            QPushButton#overrideButton:hover { background-color: #6a4d6c; }
            QComboBox, QLineEdit { background-color: #2a2a2a; border: 1px solid #6c6c6c; padding: 5px; border-radius: 4px; }
            QTextBrowser { background-color: #181818; border: 1px solid #4a4a4a; }
            QLabel { padding: 5px; }
            QSplitter::handle { background-color: #4a4a4a; }
            QSplitter::handle:vertical { height: 4px; }
            QSplitter::handle:horizontal { width: 4px; }
        """)

        # --- Member Variables ---
        self.home_dir = os.path.expanduser('~')
        self.contract_map_data = {}
        self.slither_findings = []
        self.processed_slither_findings = []
        self.selected_project_path = None
        self.selected_contract = None
        self.terminal_queue = Queue()
        self.transaction_feed_queue = Queue()
        self.is_map_ready = False
        self.map_lock = threading.Lock()
        self.monitoring_active = False
        self.monitoring_thread = None
        self.active_project_label = QLabel("Active Project: None")
        self.oz_versions = [
            "5.0.2", "5.0.1", "5.0.0",
            "4.9.6", "4.9.5", "4.9.4", "4.9.3", "4.9.2", "4.9.1", "4.9.0",
            "4.8.3", "4.8.2", "4.8.1", "4.8.0",
            "4.7.3", "4.7.2", "4.7.1", "4.7.0",
            "latest"
        ]

        # --- Main Layout ---
        main_layout = QHBoxLayout(self)
        main_splitter = QSplitter(Qt.Horizontal)

        # Left Panel
        left_panel_widget = QWidget()
        self.left_panel_layout = QVBoxLayout()
        self.setup_left_panel()
        left_panel_widget.setLayout(self.left_panel_layout)
        main_splitter.addWidget(left_panel_widget)

        # Center Panel
        center_panel_scroll = QScrollArea()
        center_panel_scroll.setWidgetResizable(True)
        center_panel_widget = QWidget()
        self.right_panel_layout = QVBoxLayout()
        self.setup_right_panel()
        center_panel_widget.setLayout(self.right_panel_layout)
        center_panel_scroll.setWidget(center_panel_widget)
        main_splitter.addWidget(center_panel_widget)

        # Right Panel (Dual Terminals)
        right_splitter = QSplitter(Qt.Vertical)
        
        analysis_group = QGroupBox("Analysis Terminal")
        analysis_layout = QVBoxLayout()
        self.terminal_output = QTextBrowser(self)
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setOpenExternalLinks(True)
        analysis_layout.addWidget(self.terminal_output)
        analysis_group.setLayout(analysis_layout)
        right_splitter.addWidget(analysis_group)

        transaction_group = QGroupBox("Live Transaction Feed")
        transaction_layout = QVBoxLayout()
        self.transaction_feed_output = QTextBrowser(self)
        self.transaction_feed_output.setReadOnly(True)
        transaction_layout.addWidget(self.transaction_feed_output)
        transaction_group.setLayout(transaction_layout)
        right_splitter.addWidget(transaction_group)

        right_splitter.setSizes([540, 540])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([350, 550, 1020])
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        # --- Timers for UI Updates ---
        self.analysis_timer = QTimer(self)
        self.analysis_timer.timeout.connect(self.update_analysis_output)
        self.analysis_timer.start(100)
        
        self.transaction_timer = QTimer(self)
        self.transaction_timer.timeout.connect(self.update_transaction_feed)
        self.transaction_timer.start(100)

    def setup_left_panel(self):
        # --- Live Analysis & Monitoring Group ---
        monitoring_group = QGroupBox("Live Analysis & Monitoring")
        monitoring_layout = QFormLayout()
        self.alchemy_api_key_input = QLineEdit()
        self.alchemy_api_key_input.setPlaceholderText("Enter your Alchemy API Key")
        self.alchemy_api_key_input.setEchoMode(QLineEdit.Password)
        monitoring_layout.addRow("Alchemy API Key:", self.alchemy_api_key_input)
        self.target_contract_dropdown = QComboBox()
        self.target_contract_dropdown.addItem("Generate Map to Populate")
        monitoring_layout.addRow("Target Contract:", self.target_contract_dropdown)
        self.monitoring_button = QPushButton("Start Monitoring")
        self.monitoring_button.clicked.connect(self.toggle_monitoring)
        monitoring_layout.addRow(self.monitoring_button)
        monitoring_group.setLayout(monitoring_layout)
        self.left_panel_layout.addWidget(monitoring_group)

        # --- Project Setup Group ---
        project_group = QGroupBox("Project Setup")
        project_layout = QFormLayout()
        self.select_project_button = QPushButton("Select Project Folder")
        project_layout.addRow(self.select_project_button)
        project_layout.addRow(self.active_project_label)
        self.source_repo_url_input = QLineEdit()
        self.source_repo_url_input.setPlaceholderText("Auto-detected. Override here if needed.")
        project_layout.addRow("Source Repo URL:", self.source_repo_url_input)
        self.prepare_project_button = QPushButton("Prepare Project (Iterative)")
        project_layout.addRow(self.prepare_project_button)
        project_group.setLayout(project_layout)
        self.left_panel_layout.addWidget(project_group)

        # --- MANUAL OVERRIDE SECTION ---
        override_group = QGroupBox("Manual Dependency Override")
        override_layout = QFormLayout()
        self.oz_version_dropdown = QComboBox()
        self.oz_version_dropdown.addItems(self.oz_versions)
        override_layout.addRow("OpenZeppelin Version:", self.oz_version_dropdown)
        self.force_install_oz_button = QPushButton("Force Install OpenZeppelin")
        self.force_install_oz_button.setObjectName("overrideButton")
        override_layout.addRow(self.force_install_oz_button)
        override_group.setLayout(override_layout)
        self.left_panel_layout.addWidget(override_group)
        
        # --- Build & Test Group ---
        build_group = QGroupBox("Build & Test")
        build_layout = QVBoxLayout()
        self.forge_build_button = QPushButton("Build Project (forge build)")
        build_layout.addWidget(self.forge_build_button)
        self.forge_clean_button = QPushButton("Clean Project (forge clean)")
        build_layout.addWidget(self.forge_clean_button)
        self.run_tests_button = QPushButton("Run All Tests (forge test)")
        build_layout.addWidget(self.run_tests_button)
        build_group.setLayout(build_layout)
        self.left_panel_layout.addWidget(build_group)

        # --- Analysis Group ---
        analysis_group = QGroupBox("Analysis & Reporting")
        analysis_layout = QVBoxLayout()
        self.generate_project_map_button = QPushButton("Generate/Refresh Project Map")
        analysis_layout.addWidget(self.generate_project_map_button)
        self.run_slither_scan_button = QPushButton("Run Slither Scan")
        analysis_layout.addWidget(self.run_slither_scan_button)
        self.generate_report_button = QPushButton("Generate Full Report")
        analysis_layout.addWidget(self.generate_report_button)
        analysis_group.setLayout(analysis_layout)
        self.left_panel_layout.addWidget(analysis_group)

        self.left_panel_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Connect Signals ---
        self.select_project_button.clicked.connect(self.select_project_folder)
        self.prepare_project_button.clicked.connect(self.prepare_project)
        self.force_install_oz_button.clicked.connect(self.force_install_oz)
        self.forge_build_button.clicked.connect(self.run_forge_build)
        self.forge_clean_button.clicked.connect(self.run_forge_clean)
        self.generate_project_map_button.clicked.connect(self.generate_contract_map)
        self.run_slither_scan_button.clicked.connect(self.run_slither_scan_only)
        self.generate_report_button.clicked.connect(self.generate_full_report)
        self.run_tests_button.clicked.connect(self.run_forge_tests_with_verbosity)

    def setup_right_panel(self):
        exploit_generation_group = QGroupBox("Exploit Generation (from Slither)")
        main_exploit_layout = QVBoxLayout()
        self.slither_vuln_dropdown = QComboBox()
        self.slither_vuln_dropdown.setEnabled(False)
        main_exploit_layout.addWidget(self.slither_vuln_dropdown)
        self.generate_exploit_button = QPushButton("Generate Exploit PoC")
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
        explorer_layout.addWidget(self.file_explorer)
        explorer_group.setLayout(explorer_layout)
        self.right_panel_layout.addWidget(explorer_group, 1)

    def update_analysis_output(self):
        while not self.terminal_queue.empty():
            self.terminal_output.append(self.terminal_queue.get_nowait())

    def update_transaction_feed(self):
        while not self.transaction_feed_queue.empty():
            self.transaction_feed_output.append(self.transaction_feed_queue.get_nowait())

    def run_command(self, command, cwd=None, on_success_callback=None):
        def target():
            try:
                log_msg = f"<b>Executing:</b> <span style='color:#87CEEB;'>{command}</span>" + (f" in {cwd}" if cwd else "") + "\n"
                self.terminal_queue.put(log_msg)
                # Use shell=True for complex commands, especially with npm/npx
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd, bufsize=1, universal_newlines=True)
                
                for line in iter(process.stdout.readline, ''):
                    self.terminal_queue.put(html.escape(line).replace('\n', '<br>'))
                process.wait()

                if process.returncode == 0:
                    if on_success_callback:
                        on_success_callback()
                else:
                    self.terminal_queue.put(f"<span style='color:orange;'>Command finished with non-zero exit code: {process.returncode}</span>")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'>Error executing command: {e}</span><br><pre>{traceback.format_exc()}</pre>")
        threading.Thread(target=target, daemon=True).start()
    
    def prepare_project(self):
        project_root = self.get_project_root()
        if not project_root:
            QMessageBox.warning(self, "Project Not Selected", "Please select a project folder first.")
            return
        reply = QMessageBox.question(self, 'Confirm Project Preparation',
                                     "This will run an iterative diagnostic process to attempt to fix build issues automatically. This may involve installing dependencies and modifying project configuration.\n\nContinue?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No: return
        self.clear_all_output()
        source_repo_url = self.source_repo_url_input.text()
        threading.Thread(target=self._prepare_project_thread, args=(project_root, source_repo_url), daemon=True).start()
    
    def _prepare_project_thread(self, project_path, source_repo_url):
        project_name = os.path.basename(project_path)
        self.terminal_queue.put(f"<h2>--- Iterative Preparation: {project_name} ---</h2>")

        self.terminal_queue.put("<b>STAGE: Discovering Remote Repository...</b>")
        effective_source_url = source_repo_url
        if not effective_source_url and os.path.isdir(os.path.join(project_path, '.git')):
            try:
                git_remote_result = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=project_path, capture_output=True, text=True, check=True)
                local_url = git_remote_result.stdout.strip()
                if local_url:
                    self.terminal_queue.put(f"   - ✅ Auto-discovered remote: {local_url}")
                    effective_source_url = local_url
            except Exception:
                self.terminal_queue.put("   - ⚠️ Could not auto-discover remote URL.")

        self.terminal_queue.put("<hr><b>STAGE: Initial Dependency Setup...</b>")
        subprocess.run("git submodule update --init --recursive", shell=True, cwd=project_path, capture_output=True)
        subprocess.run("npm install", shell=True, cwd=project_path, capture_output=True)

        max_attempts = 4
        build_succeeded = False
        tried_strategies = set()

        for attempt in range(1, max_attempts + 1):
            self.terminal_queue.put(f"<hr><h3>ATTEMPT {attempt}/{max_attempts}: Building...</h3>")
            
            self._generate_and_apply_remappings(project_path)
            subprocess.run("forge clean", shell=True, cwd=project_path, capture_output=True)
            
            build_result = subprocess.run("forge build", shell=True, cwd=project_path, capture_output=True, text=True)
            
            if build_result.returncode == 0:
                self.terminal_queue.put("<b style='color:lightgreen;'>✅ Build Succeeded!</b>")
                build_succeeded = True
                break

            self.terminal_queue.put(f"<span style='color:red;'>❌ Build Failed.</span>")
            error_log = build_result.stdout + build_result.stderr
            analysis = self.analyze_build_failure(error_log)
            
            if not analysis:
                self.terminal_queue.put(f"<pre>{html.escape(error_log)}</pre><b>Diagnosis:</b> No known automated fix.")
                break

            strategy = analysis['strategy']
            self.terminal_queue.put(f"<b>Diagnosis:</b> {analysis['reason']}")

            if strategy in tried_strategies:
                strategy = "submodule_force_sync"
                if strategy in tried_strategies:
                    self.terminal_queue.put("<b>Escalation:</b> All strategies attempted. Halting.")
                    break
            
            self.terminal_queue.put(f"<b>Strategy:</b> Applying '{strategy}' fix...")
            tried_strategies.add(strategy)
            
            fix_applied = False
            if strategy == 'oz_version_swap':
                fix_applied = self._internal_force_install_oz(project_path, analysis['recommendation'])
            elif strategy == 'repo_sync':
                if not effective_source_url:
                    self.terminal_queue.put("   - <span style='color:orange;'>Strategy requires a source URL. Halting.</span>")
                    break
                fix_applied = self._strategy_sync_from_source(project_path, effective_source_url)
            elif strategy == 'submodule_force_sync':
                fix_applied = self._strategy_submodule_sync(project_path)

            if not fix_applied:
                self.terminal_queue.put("   - <span style='color:red;'>Fix strategy failed to execute. Halting.</span>")
                break
        
        if build_succeeded:
            self.terminal_queue.put("<hr><h2>🚀 Project Preparation Complete. 🚀</h2>")
            marker_file = os.path.join(project_path, '.scanner_prepared')
            with open(marker_file, 'w') as f: f.write(datetime.now().isoformat())
        else:
            self.terminal_queue.put("<hr><h2>🛑 Automated Preparation Failed. 🛑</h2>")

    def analyze_build_failure(self, error_log):
        if "Error (5883)" in error_log and "defined twice" in error_log:
            return {"strategy": "oz_version_swap", "recommendation": "4.9.6", "reason": "OpenZeppelin version conflict."}
        if "failed to resolve file" in error_log:
            return {"strategy": "repo_sync", "reason": "Dependency mismatch (file not found)."}
        return None
    
    def _strategy_submodule_sync(self, project_path):
        self.terminal_queue.put("   - <b>Action:</b> Forcing update of all Git submodules...")
        try:
            result = subprocess.run("git submodule update --init --recursive --remote", shell=True, cwd=project_path, capture_output=True, text=True)
            if result.returncode != 0:
                self.terminal_queue.put(f"   - <span style='color:red;'>Submodule sync failed.</span><pre>{result.stderr}</pre>")
                return False
            self.terminal_queue.put("   - <b style='color:lightgreen;'>✅ Submodules successfully synced.</b>")
            return True
        except Exception as e:
            self.terminal_queue.put(f"   - <span style='color:red;'>Error during submodule sync: {e}</span>")
            return False

    def _internal_force_install_oz(self, project_path, version):
        self.terminal_queue.put(f"   - <b>Action:</b> Running `npm install @openzeppelin/contracts@{version}`...")
        result = subprocess.run(f"npm install @openzeppelin/contracts@{version}", shell=True, cwd=project_path, capture_output=True, text=True)
        if result.returncode != 0:
            self.terminal_queue.put(f"<span style='color:red;'>   - ❌ Install failed.</span><pre>{result.stderr}</pre>")
            return False
        self.terminal_queue.put("   - <b style='color:lightgreen;'>✅ Install successful.</b>")
        return True

    def _strategy_sync_from_source(self, project_path, source_repo_url):
        self.terminal_queue.put(f"   - <b>Action:</b> Syncing NPM dependencies from <a href='{source_repo_url}'>{source_repo_url}</a>...")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                clone_result = subprocess.run(["git", "clone", "--depth", "1", source_repo_url, temp_dir], capture_output=True, text=True)
                if clone_result.returncode != 0:
                    self.terminal_queue.put(f"   - <span style='color:red;'>❌ Failed to clone source repository.</span><pre>{clone_result.stderr}</pre>")
                    return False
                
                source_package_json_path = os.path.join(temp_dir, 'package.json')
                if not os.path.exists(source_package_json_path):
                    self.terminal_queue.put("   - <span style='color:orange;'>⚠️ No `package.json` found in source repository.</span>")
                    return False

                with open(source_package_json_path, 'r') as f: source_data = json.load(f)
                
                source_deps = {**source_data.get('dependencies', {}), **source_data.get('devDependencies', {})}
                deps_to_install = [f"{name}@{version}" for name, version in source_deps.items()]

                if not deps_to_install: return True

                command = f"npm install {' '.join(deps_to_install)}"
                install_result = subprocess.run(command, shell=True, cwd=project_path, capture_output=True, text=True)

                if install_result.returncode != 0:
                    self.terminal_queue.put(f"   - <span style='color:red;'>❌ Failed to install synced dependencies.</span><pre>{install_result.stderr}</pre>")
                    return False

                self.terminal_queue.put("   - <b style='color:lightgreen;'>✅ Successfully synced NPM dependencies.</b>")
                return True
            except Exception as e:
                self.terminal_queue.put(f"   - <span style='color:red;'>❌ Error during repo sync: {e}</span>")
                return False

    def find_library_folders(self, root_path):
        lib_folders = set()
        for dirpath, dirnames, _ in os.walk(root_path):
            if '.git' in dirnames: dirnames.remove('.git')
            if 'node_modules' in dirnames:
                lib_folders.add(os.path.relpath(os.path.join(dirpath, 'node_modules'), root_path))
                dirnames.remove('node_modules')
            if 'lib' in dirnames:
                lib_folders.add(os.path.relpath(os.path.join(dirpath, 'lib'), root_path))
        return sorted(list(lib_folders))

    def get_canonical_name(self, remapping_key):
        name = remapping_key.strip('/').replace('@', '')
        if 'openzeppelin-contracts-upgradeable' in name: return 'openzeppelin-contracts-upgradeable'
        if 'openzeppelin-contracts' in name: return 'openzeppelin-contracts'
        return name.split('/')[0]

    def _generate_and_apply_remappings(self, project_path):
        self.terminal_queue.put("   - ℹ️ Performing deep remapping analysis...")
        toml_path = os.path.join(project_path, 'foundry.toml')
        config = {}
        if os.path.exists(toml_path):
            with open(toml_path, 'r') as f:
                try:
                    config = toml.load(f)
                except toml.TomlDecodeError:
                    self.terminal_queue.put(f"   - ⚠️ Could not parse `foundry.toml`.")
                    return False
        
        profile = config.setdefault('profile', {}).setdefault('default', {})

        self.terminal_queue.put("     - Discovering all library folders...")
        library_paths = self.find_library_folders(project_path)
        profile['libs'] = sorted(list(set(profile.get('libs', []) + library_paths)))
        with open(toml_path, 'w') as f: toml.dump(config, f)
        
        self.terminal_queue.put("     - Generating and de-duplicating remappings...")
        try:
            raw_remappings_result = subprocess.run("forge remappings", shell=True, cwd=project_path, capture_output=True, text=True, check=True)
            all_remappings = [line for line in raw_remappings_result.stdout.strip().split('\n') if line]
            
            node_modules_remappings = [r for r in all_remappings if 'node_modules' in r]
            lib_remappings = [r for r in all_remappings if 'node_modules' not in r]
            npm_lib_names = {self.get_canonical_name(r.split('=')[0]) for r in node_modules_remappings}
            
            final_lib_remappings = [r for r in lib_remappings if self.get_canonical_name(r.split('=')[0]) not in npm_lib_names]
            
            final_remappings = sorted(list(set(node_modules_remappings + final_lib_remappings)))
            profile['remappings'] = final_remappings
            
            with open(toml_path, 'w') as f: toml.dump(config, f)
            self.terminal_queue.put("     - ✅ Deep remapping complete.")
            return True
        except (subprocess.CalledProcessError, Exception) as e:
            self.terminal_queue.put(f"     - <span style='color:red;'>❌ Forge remapping command failed: {e}</span>")
            return False

    def select_project_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.home_dir)
        if folder_name:
            self.selected_project_path = folder_name
            self.clear_all_output()
            self.terminal_queue.put(f"<b>Selected Project:</b> {folder_name}\n")
            self.file_explorer.setRootIndex(self.fs_model.index(folder_name))
            project_name = os.path.basename(folder_name)
            self.active_project_label.setText(f"Active Project: {project_name}")
            self.source_repo_url_input.clear()

    def get_project_root(self):
        return self.selected_project_path

    def clear_all_output(self):
        self.terminal_output.clear()
        if hasattr(self, 'transaction_feed_output'):
            self.transaction_feed_output.clear()
        
    def run_forge_build(self):
        project_root = self.get_project_root()
        if not project_root: return
        self.run_command(f"forge build", cwd=project_root)

    def run_forge_clean(self):
        project_root = self.get_project_root()
        if not project_root: return
        self.run_command(f"forge clean", cwd=project_root, on_success_callback=self._on_clean_success)
        
    def _on_clean_success(self):
        marker_file = os.path.join(self.get_project_root(), '.scanner_prepared')
        if os.path.exists(marker_file):
            os.remove(marker_file)
            self.terminal_queue.put("🧹 Preparation marker file removed.")

    def run_forge_tests_with_verbosity(self):
        project_root = self.get_project_root()
        if not project_root: return
        self.run_command(f"forge test -vvv", cwd=project_root)
        
    def on_file_explorer_activated(self, index):
        file_path = self.fs_model.filePath(index)
        if os.path.isfile(file_path):
            self.clear_all_output()
            self.terminal_queue.put(f"<b>Displaying content for:</b> {os.path.basename(file_path)}\n")
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    self.terminal_queue.put(f"<pre>{html.escape(f.read())}</pre>")
            except Exception as e:
                self.terminal_queue.put(f"<span style='color:red;'>Could not read file: {e}</span>")
    
    def generate_full_report(self):
        project_root = self.get_project_root()
        if not project_root:
            QMessageBox.warning(self, "Project Not Selected", "Please select a project folder first.")
            return
        self.clear_all_output()
        self.run_command(f"slither . --sarif-file slither_report.sarif", cwd=project_root, on_success_callback=lambda: self.terminal_queue.put("Full report generated."))

    def run_slither_scan_only(self):
        project_root = self.get_project_root()
        if not project_root: return
        self.run_command(f"slither .", cwd=project_root)
        
    def generate_slither_exploit(self):
        self.terminal_queue.put("Exploit generation not yet implemented.")

    def generate_contract_map(self):
        if not Slither:
            QMessageBox.critical(self, "Slither Not Found", "Py-Slither is required for this feature but could not be imported.")
            return
        # Placeholder for contract map logic
        self.terminal_queue.put("Contract map generation not yet fully implemented.")

    def force_install_oz(self):
        # Placeholder for manual override logic
        self.terminal_queue.put("Manual OZ install not yet fully implemented.")

    def toggle_monitoring(self):
        # Placeholder for monitoring logic
        self.terminal_queue.put("Live monitoring not yet fully implemented.")


if __name__ == '__main__':
    if sys.platform.startswith('linux') and 'WAYLAND_DISPLAY' in os.environ and 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    app = QApplication(sys.argv)
    window = Application()
    window.show()
    sys.exit(app.exec_())

