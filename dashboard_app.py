# Save this code as dashboard_app.py
# To run:
# 1. Open terminal
# 2. pip3 install Flask requests
# 3. python3 dashboard_app.py
# 4. Open your browser to http://127.0.0.1:5000

from flask import Flask, request, render_template_string, jsonify
import re
import os
import sqlite3
import json
import requests
import hashlib
import threading
import time
import random

# --- FLASK APP & DATABASE SETUP ---
app = Flask(__name__)
DB_FILE = "dashboard.db"

# --- State Management for Background Task ---
enrichment_lock = threading.Lock()
# <<< CHANGED: Added 'wait_time' for UI feedback and a thread-safe stop event.
enrichment_status_global = {"is_running": False, "progress": 0, "total": 0, "message": "Idle", "wait_time": 0}
enrichment_stop_event = threading.Event()


def get_db_conn():
    """Gets a database connection."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            report_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            scanner TEXT NOT NULL,
            title TEXT NOT NULL,
            level TEXT NOT NULL,
            description TEXT,
            location TEXT,
            gemini_info TEXT,
            gemini_test TEXT,
            enrichment_status TEXT DEFAULT 'PENDING',
            enrichment_error TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')
    try:
        cursor.execute("ALTER TABLE findings ADD COLUMN enrichment_error TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

# --- HTML & JAVASCRIPT TEMPLATE ---
# <<< CHANGED: Added a Stop button and logic to display the wait countdown.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local Security Report Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
        .card { transition: transform 0.2s ease, box-shadow 0.2s ease; height: 100%; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.15); }
        #drop-zone { border: 2px dashed #4A5568; transition: all 0.3s; }
        #drop-zone.drag-over { border-color: #3B82F6; background-color: #252c3b; }
        .filter-select, .input-field { background-color: #374151; border-color: #4B5563; color: #D1D5DB; }
        .loader { border: 2px solid #4A5568; border-top: 2px solid #3B82F6; border-radius: 50%; width: 16px; height: 16px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-900 text-gray-200 p-4 sm:p-8">
    <div class="container mx-auto max-w-7xl">
        <div class="header text-center mb-10">
            <h1 class="text-4xl sm:text-5xl font-bold text-white">Local Security Dashboard</h1>
            <p class="text-lg text-gray-400 mt-2">Upload reports, track findings, and enrich with AI analysis.</p>
        </div>

        <div class="max-w-3xl mx-auto mb-12 p-6 bg-gray-800/50 rounded-xl border border-gray-700">
            <h2 class="text-2xl font-bold text-white mb-4">Upload New Report</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <input id="project-name" type="text" placeholder="Project Name (e.g., inverse-protocol)" class="input-field w-full p-2 rounded-md">
                <div class="flex gap-2">
                    <input id="api-key" type="password" placeholder="Google Gemini API Key" class="input-field w-full p-2 rounded-md">
                    <button id="test-api-key" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-1.5 rounded-md flex-shrink-0">Test Key</button>
                </div>
            </div>
            <div id="drop-zone" class="relative flex flex-col items-center justify-center w-full p-8 bg-gray-800 border-gray-700 rounded-xl cursor-pointer">
                <svg class="w-12 h-12 text-gray-500 mb-4" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"/></svg>
                <p class="mb-2 text-lg text-gray-400"><span class="font-semibold">Click to upload</span> or drag & drop</p>
                <p class="text-sm text-gray-500">Accepts <code>report.md</code> files</p>
                <input id="file-input" type="file" class="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer" accept=".md">
            </div>
            <div id="upload-status" class="text-center font-mono text-sm text-gray-400 mt-4 h-5"></div>
        </div>

        <div class="flex flex-wrap gap-4 justify-center mb-4 items-center bg-gray-800 p-4 rounded-lg">
            <div class="flex items-center gap-2">
                <label for="project-filter" class="font-medium text-gray-300">Project:</label>
                <select id="project-filter" class="filter-select rounded-md px-3 py-1.5"></select>
            </div>
            <div class="flex items-center gap-2">
                <label for="scanner-filter" class="font-medium text-gray-300">Scanner:</label>
                <select id="scanner-filter" class="filter-select rounded-md px-3 py-1.5">
                    <option value="all">All</option><option value="Slither">Slither</option><option value="Aderyn">Aderyn</option><option value="Wake">Wake</option>
                </select>
            </div>
            <div class="flex items-center gap-2">
                <label for="rating-filter" class="font-medium text-gray-300">Severity:</label>
                <select id="rating-filter" class="filter-select rounded-md px-3 py-1.5">
                    <option value="all">All</option><option value="CRITICAL">Critical</option><option value="HIGH">High</option><option value="MEDIUM">Medium</option><option value="LOW">Low</option><option value="INFO">Info</option>
                </select>
            </div>
        </div>
        
        <div id="enrichment-controls" class="hidden text-center mb-8 p-4 bg-gray-800 rounded-lg">
            <button id="enrich-btn" class="bg-green-600 hover:bg-green-700 text-white font-semibold px-4 py-2 rounded-md">Start Enrichment</button>
            <button id="stop-btn" class="hidden bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 rounded-md">Stop Enrichment</button>
            <div id="enrichment-status" class="mt-3 text-gray-400 h-5"></div>
            <div id="progress-bar-container" class="w-full bg-gray-700 rounded-full h-2.5 mt-2 hidden">
                <div id="progress-bar" class="bg-blue-600 h-2.5 rounded-full" style="width: 0%"></div>
            </div>
        </div>

        <div id="report-cards" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"></div>
    </div>

    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const uploadStatus = document.getElementById('upload-status');
        const cardsContainer = document.getElementById('report-cards');
        const projectFilter = document.getElementById('project-filter');
        const scannerFilter = document.getElementById('scanner-filter');
        const ratingFilter = document.getElementById('rating-filter');
        const apiKeyInput = document.getElementById('api-key');
        const testApiKeyBtn = document.getElementById('test-api-key');
        const enrichmentControls = document.getElementById('enrichment-controls');
        const enrichBtn = document.getElementById('enrich-btn');
        const stopBtn = document.getElementById('stop-btn');
        const enrichmentStatus = document.getElementById('enrichment-status');
        const progressBarContainer = document.getElementById('progress-bar-container');
        const progressBar = document.getElementById('progress-bar');
        
        let statusInterval = null;

        document.addEventListener('DOMContentLoaded', () => {
            loadProjects();
            apiKeyInput.value = localStorage.getItem('geminiApiKey') || '';
        });

        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', () => { if (fileInput.files.length > 0) handleFileUpload(fileInput.files[0]); });
        projectFilter.addEventListener('change', () => loadFindingsForProject(projectFilter.value));
        scannerFilter.addEventListener('change', () => loadFindingsForProject(projectFilter.value));
        ratingFilter.addEventListener('change', () => loadFindingsForProject(projectFilter.value));
        apiKeyInput.addEventListener('change', () => localStorage.setItem('geminiApiKey', apiKeyInput.value));
        testApiKeyBtn.addEventListener('click', testApiKey);
        enrichBtn.addEventListener('click', startEnrichment);
        stopBtn.addEventListener('click', stopEnrichment);

        function testApiKey() {
            const apiKey = apiKeyInput.value.trim();
            if (!apiKey) {
                uploadStatus.textContent = 'Please enter an API key.';
                uploadStatus.className = 'text-center font-mono text-sm text-yellow-400 mt-4 h-5';
                return;
            }
            uploadStatus.textContent = 'Testing API key...';
            uploadStatus.className = 'text-center font-mono text-sm text-yellow-400 mt-4 h-5';
            fetch('/api/test_gemini', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ apiKey: apiKey })
            }).then(res => res.json()).then(data => {
                uploadStatus.textContent = data.success ? 'API Key is valid!' : `API Key Test Failed: ${data.error}`;
                uploadStatus.className = data.success ? 'text-center font-mono text-sm text-green-400 mt-4 h-5' : 'text-center font-mono text-sm text-red-400 mt-4 h-5';
            });
        }
        
        function loadProjects() {
            fetch('/api/projects').then(res => res.json()).then(projects => {
                const currentVal = projectFilter.value;
                projectFilter.innerHTML = '<option value="">Select a Project</option>';
                projects.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.id;
                    option.textContent = p.name;
                    projectFilter.appendChild(option);
                });
                if (currentVal) projectFilter.value = currentVal;
            });
        }

        function handleFileUpload(file) {
            const projectName = document.getElementById('project-name').value.trim();
            if (!projectName || !file) {
                uploadStatus.textContent = 'Project Name and File are required.';
                uploadStatus.className = 'text-center font-mono text-sm text-red-400 mt-4 h-5';
                return;
            }
            uploadStatus.textContent = 'Uploading report...';
            const formData = new FormData();
            formData.append('file', file);
            formData.append('projectName', projectName);
            fetch('/upload', { method: 'POST', body: formData }).then(res => res.json()).then(data => {
                if (data.error) {
                    uploadStatus.textContent = `Error: ${data.error}`;
                    uploadStatus.className = 'text-center font-mono text-sm text-red-400 mt-4 h-5';
                } else {
                    uploadStatus.textContent = data.message;
                    uploadStatus.className = 'text-center font-mono text-sm text-green-400 mt-4 h-5';
                    document.getElementById('project-name').value = '';
                    loadProjects();
                    setTimeout(() => {
                       projectFilter.value = data.project_id;
                       loadFindingsForProject(data.project_id);
                    }, 200);
                }
            });
        }
        
        function startEnrichment() {
            const projectId = projectFilter.value;
            const apiKey = apiKeyInput.value.trim();
            if (!projectId || !apiKey) {
                alert('Please select a project and enter an API key.');
                return;
            }
            enrichBtn.classList.add('hidden');
            stopBtn.classList.remove('hidden');
            stopBtn.disabled = false;
            stopBtn.textContent = 'Stop Enrichment';

            fetch(`/api/enrich/${projectId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ apiKey: apiKey })
            }).then(res => res.json()).then(data => {
                if(data.error) {
                    enrichmentStatus.textContent = data.error;
                    enrichBtn.classList.remove('hidden');
                    stopBtn.classList.add('hidden');
                } else {
                    checkEnrichmentStatus();
                }
            });
        }

        function stopEnrichment() {
            stopBtn.disabled = true;
            stopBtn.textContent = 'Stopping...';
            fetch('/api/stop_enrichment', {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    enrichmentStatus.textContent = data.message || data.error;
                });
        }

        function checkEnrichmentStatus() {
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(() => {
                fetch('/api/enrichment_status').then(res => res.json()).then(status => {
                    if (status.is_running) {
                        progressBarContainer.classList.remove('hidden');
                        const progressPercentage = status.total > 0 ? (status.progress / status.total) * 100 : 0;
                        progressBar.style.width = `${progressPercentage}%`;
                        
                        if (status.wait_time && status.wait_time > 0) {
                            enrichmentStatus.textContent = `Rate limit hit. Paused for ${Math.ceil(status.wait_time)} seconds...`;
                        } else {
                            enrichmentStatus.textContent = status.message;
                        }
                    } else {
                        progressBarContainer.classList.add('hidden');
                        enrichBtn.classList.remove('hidden');
                        stopBtn.classList.add('hidden');
                        enrichmentStatus.textContent = status.message || "Idle";
                        clearInterval(statusInterval);
                        loadFindingsForProject(projectFilter.value, true);
                    }
                });
            }, 2000);
        }

        function loadFindingsForProject(projectId, force_refresh = false) {
            if (!projectId) {
                cardsContainer.innerHTML = '';
                uploadStatus.textContent = '';
                enrichmentControls.classList.add('hidden');
                return;
            }
            if (!force_refresh) {
                 cardsContainer.innerHTML = '<div class="col-span-full flex justify-center"><div class="loader"></div></div>';
            }
            
            const scanner = scannerFilter.value;
            const rating = ratingFilter.value;
            
            fetch(`/api/findings/${projectId}?scanner=${scanner}&rating=${rating}`).then(res => res.json()).then(cards => {
                renderCards(cards);
                const hasPending = cards.some(c => c.enrichment_status === 'PENDING' || c.enrichment_status === 'FAILED');
                if (hasPending) {
                    enrichmentControls.classList.remove('hidden');
                } else {
                    enrichmentControls.classList.add('hidden');
                }
            });
        }

        function renderCards(cards) {
            cardsContainer.innerHTML = '';
            if (!cards || cards.length === 0) {
                cardsContainer.innerHTML = '<p class="text-center text-gray-500 col-span-full">No findings match current filters.</p>';
                return;
            }
            cards.forEach(card => {
                const cardElement = document.createElement('div');
                cardElement.className = 'card bg-gray-800 rounded-xl border border-gray-700 p-6 flex flex-col';
                renderSingleCard(cardElement, card);
                cardsContainer.appendChild(cardElement);
            });
        }

        function renderSingleCard(cardElement, card) {
            const threatColorClasses = {'CRITICAL': 'bg-red-800 text-red-100', 'HIGH': 'bg-orange-700 text-orange-100', 'MEDIUM': 'bg-yellow-600 text-yellow-100', 'LOW': 'bg-blue-700 text-blue-100', 'INFO': 'bg-gray-600 text-gray-200'};
            const threatClass = threatColorClasses[card.level] || 'bg-gray-700 text-gray-200';
            
            let geminiSection = '';
            if (card.enrichment_status === 'COMPLETED') {
                geminiSection = `
                        <div><h3 class="font-semibold text-gray-300 border-b border-gray-700 pb-1 mb-2 mt-4">Gemini Analysis</h3><p class="whitespace-pre-wrap text-sm">${card.gemini_info || 'N/A'}</p></div>
                        <div><h3 class="font-semibold text-gray-300 border-b border-gray-700 pb-1 mb-2 mt-4">Forge Test Example</h3><pre class="bg-gray-900 p-3 rounded-md overflow-x-auto text-xs"><code>${card.gemini_test || 'N/A'}</code></pre></div>`;
            } else if (card.enrichment_status === 'PENDING') {
                 geminiSection = '<div class="mt-4 flex items-center gap-2 text-yellow-400"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span>Queued for analysis...</span></div>';
            } else if (card.enrichment_status === 'SKIPPED') {
                 geminiSection = `<div class="mt-4 flex items-center gap-2 text-blue-400"><svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg><span>AI Analysis Skipped (Informational)</span></div>`;
            } else if (card.enrichment_status === 'FAILED') {
                 geminiSection = `<div class="mt-4 text-red-400"><p class="font-bold">AI Enrichment Failed</p><p class="text-xs mt-1">${card.enrichment_error || 'Unknown error.'}</p></div>`;
            }

            cardElement.innerHTML = `
                <div class="flex items-start justify-between mb-3"><h2 class="text-xl font-semibold text-white pr-2">${card.title}</h2><span class="text-xs font-mono bg-gray-700 px-2 py-1 rounded flex-shrink-0">${card.scanner}</span></div>
                <div class="mb-4"><span class="inline-block ${threatClass} text-sm font-medium px-3 py-1 rounded-full">${card.level}</span></div>
                <div class="text-gray-400 space-y-4 text-sm flex-grow">
                    <div><h3 class="font-semibold text-gray-300 border-b border-gray-700 pb-1 mb-2">Description</h3><p>${card.description}</p></div>
                    <div><h3 class="font-semibold text-gray-300 border-b border-gray-700 pb-1 mb-2">Location</h3><p class="font-mono break-words">${card.location}</p></div>
                    <div class="gemini-section">${geminiSection}</div>
                </div>`;
        }
    </script>
</body>
</html>
"""

# --- MARKDOWN PARSING LOGIC ---
def get_severity_from_slither(detector):
    detector = detector.lower()
    if 'reentrancy' in detector or 'uninitialized' in detector: return 'CRITICAL'
    if 'arbitrary-from' in detector or 'calls-inside-a-loop' in detector: return 'HIGH'
    if 'dangerous-strict' in detector or 'divide-before-multiply' in detector or 'unchecked-transfer' in detector: return 'MEDIUM'
    return 'LOW'

def parse_slither_report(content):
    cards = []
    detector_blocks = re.findall(r"INFO:Detectors:\n(.*?)(?=INFO:Detectors:|\Z)", content, re.DOTALL)
    for block in detector_blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines: continue
        location_line = lines[0]
        description, location = (re.match(r"(.+?)\s*\((.*?)\)", location_line).groups() if re.match(r"(.+?)\s*\((.*?)\)", location_line) else (location_line, "N/A"))
        ref_match = re.search(r"Reference: https://.+?#(.+)", block)
        detector_name = ref_match.group(1) if ref_match else "Unknown Issue"
        cards.append({'scanner': 'Slither', 'title': detector_name.replace('-', ' ').title(), 'level': get_severity_from_slither(detector_name), 'description': description.strip(), 'location': location.strip()})
    return cards

def parse_aderyn_report(content):
    cards = []
    issue_blocks = re.findall(r"##\s*(H|L)-\d+:\s*(.*?)\n\n(.*?)(?=##\s*(H|L)-\d+:|\Z)", content, re.DOTALL)
    for block in issue_blocks:
        severity_char, title, body, _ = block
        locations = re.findall(r"- Found in (.*?)\s*\[Line: \d+\]", body)
        description = body.split('\n\n')[0].replace('\n', ' ').strip()
        cards.append({'scanner': 'Aderyn', 'title': title.strip(), 'level': 'HIGH' if severity_char == 'H' else 'LOW', 'description': description, 'location': locations[0] if locations else "N/A"})
    return cards

def parse_wake_report(content):
    cards = []
    wake_blocks = re.findall(r"╭─\s*\[(.*?)\].*?\[(.*?)\].*?─╮\n(.*?)\n╰─\s*(.*?)\s*─+", content, re.DOTALL)
    for block in wake_blocks:
        severity_tags, issue_type, body, location = block
        level = 'INFO'
        if 'CRITICAL' in severity_tags: level = 'CRITICAL'
        elif 'HIGH' in severity_tags: level = 'HIGH'
        elif 'MEDIUM' in severity_tags: level = 'MEDIUM'
        elif 'LOW' in severity_tags: level = 'LOW'
        description_match = re.search(r"│\s*❱\s*\d+\s*(.*)", body)
        description = description_match.group(1).strip() if description_match else f"Wake detector '{issue_type}' triggered."
        cards.append({'scanner': 'Wake', 'title': issue_type.replace('-', ' ').title(), 'level': level, 'description': description, 'location': location.strip()})
    return cards

def parse_markdown_report(md_content):
    all_cards = []
    slither_content = re.search(r"## Slither Analysis(.*?)(?=##\s*\w+\s*Analysis|\Z)", md_content, re.DOTALL)
    aderyn_content = re.search(r"## Aderyn Analysis(.*?)(?=##\s*\w+\s*Analysis|\Z)", md_content, re.DOTALL)
    wake_content = re.search(r"## Wake Analysis(.*?)(?=##\s*\w+\s*Analysis|\Z)", md_content, re.DOTALL)
    if slither_content: all_cards.extend(parse_slither_report(slither_content.group(1)))
    if aderyn_content: all_cards.extend(parse_aderyn_report(aderyn_content.group(1)))
    if wake_content: all_cards.extend(parse_wake_report(wake_content.group(1)))
    return all_cards

# --- GEMINI API HELPER ---
def enrich_finding_with_gemini(finding, api_key):
    if not api_key: return None, None, "FAILED", "API Key was not provided."
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    prompt = f"""Analyze the following smart contract security finding and provide a response in JSON format.
Finding Details:
- Title: {finding['title']}
- Description: {finding['description']}
- Location: {finding['location']}
- Severity: {finding['level']}
Your task is to return a single JSON object with two keys: "exploit_details" and "forge_test".
1. "exploit_details": In this string, provide a clear, concise explanation of the vulnerability. Describe how it could be exploited. Include links to 1-2 relevant articles (e.g., SWC registry, Ethernaut, security blogs).
2. "forge_test": In this string, provide a sample "forge test" in Solidity. The test must be a complete, runnable function inside a contract inheriting from `Test`. It should demonstrate a proof-of-concept for the vulnerability. If a specific PoC is not possible, provide a template test showing how one would check for this class of issue.
Return ONLY the JSON object."""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'}, timeout=60)
        response.raise_for_status()
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "").strip())
        return data.get("exploit_details"), data.get("forge_test"), "COMPLETED", None
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error: {e.response.status_code}. Check API key or Gemini status."
        return None, None, "FAILED", error_msg
    except Exception as e:
        return None, None, "FAILED", f"An unexpected error occurred: {str(e)}"

def call_gemini_with_backoff(finding, api_key):
    max_retries = 5
    base_delay = 5
    for i in range(max_retries):
        if enrichment_stop_event.is_set(): return None, None, "FAILED", "Process stopped by user."
        gemini_info, gemini_test, status, error = enrich_finding_with_gemini(finding, api_key)
        if status != "FAILED" or "429" not in (error or ""):
            return gemini_info, gemini_test, status, error
        delay = base_delay * (2 ** i) + (random.uniform(0, 1))
        with enrichment_lock:
            enrichment_status_global['wait_time'] = delay
        for _ in range(int(delay)):
            if enrichment_stop_event.is_set(): return None, None, "FAILED", "Process stopped by user."
            time.sleep(1)
        with enrichment_lock:
            enrichment_status_global['wait_time'] = 0
    return None, None, "FAILED", "Failed after multiple retries due to rate limiting (429)."

# <<< CHANGED: Now checks the stop event and has a safer default delay.
def enrich_findings_in_background(project_id, api_key):
    global enrichment_status_global
    with enrichment_lock:
        if enrichment_status_global["is_running"]: return
        enrichment_stop_event.clear()
        enrichment_status_global = {"is_running": True, "progress": 0, "total": 0, "message": "Preparing...", "wait_time": 0}

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE findings SET enrichment_status = 'SKIPPED', enrichment_error = 'Informational finding, skipped.' WHERE project_id = ? AND level = 'INFO' AND (enrichment_status = 'PENDING' OR enrichment_status = 'FAILED')", (project_id,))
    cursor.execute("UPDATE findings SET enrichment_status = 'PENDING' WHERE project_id = ? AND enrichment_status = 'FAILED'", (project_id,))
    conn.commit()
    cursor.execute("SELECT * FROM findings WHERE project_id = ? AND enrichment_status = 'PENDING'", (project_id,))
    findings_to_enrich = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not findings_to_enrich:
        with enrichment_lock:
            enrichment_status_global = {"is_running": False, "message": "No actionable findings to enrich."}
        return

    with enrichment_lock:
        enrichment_status_global.update({"total": len(findings_to_enrich), "message": "Starting enrichment..."})

    for i, finding in enumerate(findings_to_enrich):
        if enrichment_stop_event.is_set():
            with enrichment_lock:
                enrichment_status_global["message"] = "Enrichment stopped by user."
            break
        with enrichment_lock:
            enrichment_status_global.update({"progress": i, "message": f"Enriching {i+1}/{len(findings_to_enrich)}: {finding['title']}"})
        
        gemini_info, gemini_test, status, error = call_gemini_with_backoff(finding, api_key)
        
        conn = get_db_conn()
        conn.cursor().execute("UPDATE findings SET gemini_info = ?, gemini_test = ?, enrichment_status = ?, enrichment_error = ? WHERE id = ?", (gemini_info, gemini_test, status, error, finding['id']))
        conn.commit()
        conn.close()
        
        if status == "COMPLETED":
            time.sleep(2) # Proactive 2-second delay to stay under limits

    with enrichment_lock:
        if not enrichment_stop_event.is_set():
            enrichment_status_global["message"] = "Enrichment complete."
        enrichment_status_global["is_running"] = False

# --- FLASK API ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/test_gemini', methods=['POST'])
def test_gemini():
    api_key = request.json.get('apiKey')
    if not api_key: return jsonify({'success': False, 'error': 'No API key provided.'})
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    try:
        response = requests.post(api_url, json={"contents": [{"parts": [{"text": "Hello"}]}]}, timeout=10)
        return jsonify({'success': True}) if response.status_code == 200 else jsonify({'success': False, 'error': f"API Error: {response.text}"})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/projects', methods=['GET'])
def get_projects():
    conn = get_db_conn()
    projects = [dict(row) for row in conn.cursor().execute("SELECT id, name FROM projects ORDER BY name")]
    conn.close()
    return jsonify(projects)

@app.route('/api/findings/<int:project_id>', methods=['GET'])
def get_findings(project_id):
    scanner = request.args.get('scanner', 'all')
    rating = request.args.get('rating', 'all')
    conn = get_db_conn()
    query = "SELECT * FROM findings WHERE project_id = ?"
    params = [project_id]
    if scanner != 'all':
        query += " AND scanner = ?"
        params.append(scanner)
    if rating != 'all':
        query += " AND level = ?"
        params.append(rating)
    findings = [dict(row) for row in conn.cursor().execute(query, params)]
    conn.close()
    findings.sort(key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}.get(x['level'], 99))
    return jsonify(findings)

@app.route('/api/enrich/<int:project_id>', methods=['POST'])
def start_enrichment_route(project_id):
    if enrichment_status_global["is_running"]: return jsonify({'error': 'An enrichment process is already running.'}), 409
    api_key = request.json.get('apiKey')
    if not api_key: return jsonify({'error': 'API Key is required.'}), 400
    threading.Thread(target=enrich_findings_in_background, args=(project_id, api_key)).start()
    return jsonify({'message': 'Enrichment process started.'})

# <<< CHANGED: New endpoint to handle stopping the process.
@app.route('/api/stop_enrichment', methods=['POST'])
def stop_enrichment_route():
    if enrichment_status_global["is_running"]:
        enrichment_stop_event.set()
        return jsonify({'message': 'Stop signal sent. Finishing current item...'})
    return jsonify({'error': 'No enrichment process is running.'}), 404

@app.route('/api/enrichment_status')
def get_enrichment_status():
    with enrichment_lock:
        return jsonify(enrichment_status_global)

@app.route('/upload', methods=['POST'])
def upload_file():
    project_name = request.form.get('projectName')
    file = request.files.get('file')
    if not all([project_name, file]): return jsonify({'error': 'Project name and file are required.'}), 400
    md_content = file.read()
    report_hash = hashlib.sha256(md_content).hexdigest()
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE name = ? AND report_hash = ?", (project_name, report_hash))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'This exact report has already been uploaded for this project.'}), 409
    try:
        cursor.execute("INSERT INTO projects (name, report_hash) VALUES (?, ?)", (project_name, report_hash))
        project_id = cursor.lastrowid
        cards = parse_markdown_report(md_content.decode('utf-8'))
        if not cards:
            conn.rollback()
            return jsonify({'error': 'Could not find any valid findings in the report file.'}), 400
        for card in cards:
            cursor.execute("INSERT INTO findings (project_id, scanner, title, level, description, location) VALUES (?, ?, ?, ?, ?, ?)", (project_id, card['scanner'], card['title'], card['level'], card['description'], card['location']))
        conn.commit()
        return jsonify({'message': f'Successfully uploaded report for {project_name}.', 'project_id': project_id})
    except sqlite3.IntegrityError:
        return jsonify({'error': f'A project named "{project_name}" already exists. Please use a new name.'}), 409
    except Exception as e:
        return jsonify({'error': f'An internal error occurred: {e}'}), 500
    finally:
        conn.close()

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
