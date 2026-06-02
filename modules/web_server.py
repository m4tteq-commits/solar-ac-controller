"""Web UI - Dashboard în limba română cu Tailwind CSS."""
import logging
import json
from datetime import datetime

from config import settings

logger = logging.getLogger('web')

try:
    from flask import Flask, render_template_string, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    logger.warning("Flask neinstalat. Web UI dezactivat.")
    FLASK_AVAILABLE = False


# Template HTML pentru dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar AC Controller</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body { background: #0f172a; }
        .card { background: #1e293b; border-color: #334155; }
        .glow-green { box-shadow: 0 0 20px rgba(34, 197, 94, 0.15); }
        .glow-red { box-shadow: 0 0 20px rgba(239, 68, 68, 0.15); }
        @keyframes pulse-sun {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .animate-sun { animation: pulse-sun 3s ease-in-out infinite; }
    </style>
</head>
<body class="text-slate-200 min-h-screen">
    <!-- Header -->
    <header class="bg-gradient-to-r from-slate-800 via-slate-900 to-slate-800 border-b-2 border-amber-500 px-6 py-4">
        <div class="max-w-5xl mx-auto flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold text-amber-500">
                    <i class="fas fa-sun animate-sun mr-2"></i>Solar AC Controller
                </h1>
                <p class="text-slate-400 text-sm mt-1">Automatizare aer condiționat bazată pe energie solară</p>
            </div>
            <div class="text-right">
                <div id="connection-status" class="text-xs text-slate-500">
                    <i class="fas fa-circle text-green-500 mr-1"></i>Conectat
                </div>
                <div id="update-time" class="text-xs text-slate-500 mt-1">Ultima actualizare: ---</div>
            </div>
        </div>
    </header>

    <main class="max-w-5xl mx-auto p-4 sm:p-6">
        <!-- Stare AC + Control Manual -->
        <div class="card rounded-xl border p-4 mb-6">
            <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="flex items-center gap-3">
                    <span id="ac-icon" class="text-3xl">❄️</span>
                    <div>
                        <div id="ac-status" class="text-xl font-bold">AC: ---</div>
                        <div id="ac-mode" class="text-sm text-slate-400">---</div>
                    </div>
                </div>
                <div class="flex gap-2">
                    <button onclick="manualOn()" class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg font-semibold transition">
                        <i class="fas fa-power-off mr-1"></i>Pornește
                    </button>
                    <button onclick="manualOff()" class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-semibold transition">
                        <i class="fas fa-power-off mr-1"></i>Oprește
                    </button>
                    <button onclick="manualAuto()" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold transition">
                        <i class="fas fa-robot mr-1"></i>Auto
                    </button>
                </div>
            </div>
        </div>

        <!-- Metrici principale -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
            <!-- Producție solară -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-sun text-amber-500 mr-1"></i>Producție solară</div>
                <div id="solar" class="text-2xl font-bold text-amber-500">---</div>
                <div class="text-slate-500 text-xs">kW</div>
            </div>
            <!-- Consum casă -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-home text-orange-500 mr-1"></i>Consum casă</div>
                <div id="consum" class="text-2xl font-bold text-orange-500">---</div>
                <div class="text-slate-500 text-xs">kW</div>
            </div>
            <!-- Surplus -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-chart-line text-green-500 mr-1"></i>Surplus</div>
                <div id="surplus" class="text-2xl font-bold">---</div>
                <div class="text-slate-500 text-xs">kW</div>
            </div>
            <!-- Baterie -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-battery-three-quarters text-purple-500 mr-1"></i>Baterie</div>
                <div id="battery" class="text-2xl font-bold text-purple-500">---</div>
                <div class="text-slate-500 text-xs">%</div>
            </div>
            <!-- T° interior -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-thermometer-half text-sky-500 mr-1"></i>T° interior</div>
                <div id="temp-in" class="text-2xl font-bold text-sky-500">---</div>
                <div class="text-slate-500 text-xs">°C</div>
            </div>
            <!-- T° exterior -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-cloud-sun text-sky-400 mr-1"></i>T° exterior</div>
                <div id="temp-out" class="text-2xl font-bold text-sky-400">---</div>
                <div class="text-slate-500 text-xs">°C</div>
            </div>
            <!-- Sursă date -->
            <div class="card rounded-xl border p-4 text-center">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-wifi text-emerald-500 mr-1"></i>Sursă</div>
                <div id="source" class="text-lg font-bold text-emerald-500">---</div>
                <div class="text-slate-500 text-xs">invertor</div>
            </div>
            <!-- Surplus vizual (bar) -->
            <div class="card rounded-xl border p-4 text-center col-span-2 sm:col-span-1">
                <div class="text-slate-400 text-xs mb-2"><i class="fas fa-gauge-high text-amber-400 mr-1"></i>Surplus vs Prag</div>
                <div class="w-full bg-slate-700 rounded-full h-4 mt-2">
                    <div id="surplus-bar" class="bg-green-500 h-4 rounded-full transition-all" style="width: 0%"></div>
                </div>
                <div id="surplus-text" class="text-xs text-slate-400 mt-1">---</div>
            </div>
        </div>

        <!-- Ultima decizie -->
        <div class="card rounded-xl border p-4 mb-6">
            <div class="flex items-start gap-3">
                <i class="fas fa-clipboard-check text-amber-500 mt-1"></i>
                <div>
                    <div class="text-sm text-slate-400">Ultima decizie</div>
                    <div id="last-decision" class="font-semibold">---</div>
                    <div id="last-reason" class="text-sm text-slate-400 mt-1">---</div>
                </div>
            </div>
        </div>

        <!-- Setări -->
        <div class="card rounded-xl border p-5 mb-6">
            <h3 class="text-amber-500 font-bold text-lg mb-4">
                <i class="fas fa-cog mr-2"></i>Setări Control
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                    <label class="text-slate-400 text-sm block mb-1">Prag Surplus Pornire (kW)</label>
                    <input type="number" id="set-surplus" step="0.1" value="1.4"
                        class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:border-amber-500 focus:outline-none">
                </div>
                <div>
                    <label class="text-slate-400 text-sm block mb-1">Temperatură Interioară Minimă (°C)</label>
                    <input type="number" id="set-temp" step="0.5" value="24"
                        class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:border-amber-500 focus:outline-none">
                </div>
                <div>
                    <label class="text-slate-400 text-sm block mb-1">Ora Pornire</label>
                    <input type="number" id="set-start" min="0" max="23" value="9"
                        class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:border-amber-500 focus:outline-none">
                </div>
                <div>
                    <label class="text-slate-400 text-sm block mb-1">Ora Oprire</label>
                    <input type="number" id="set-end" min="0" max="23" value="18"
                        class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:border-amber-500 focus:outline-none">
                </div>
            </div>
            <button onclick="saveSettings()" class="mt-4 px-6 py-2 bg-amber-500 hover:bg-amber-400 text-slate-900 rounded-lg font-bold transition">
                <i class="fas fa-save mr-2"></i>Salvează Setările
            </button>
        </div>

        <!-- Jurnal -->
        <div class="card rounded-xl border p-5">
            <h3 class="text-amber-500 font-bold text-lg mb-4">
                <i class="fas fa-scroll mr-2"></i>Jurnal Activitate
            </h3>
            <div id="log-container" class="bg-slate-900 rounded-lg p-3 max-h-48 overflow-y-auto font-mono text-xs text-slate-400">
                <div class="py-1">Se încarcă...</div>
            </div>
        </div>
    </main>

    <script>
        let autoRefresh;

        function fetchStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    // AC status
                    const acEl = document.getElementById('ac-status');
                    const acIcon = document.getElementById('ac-icon');
                    const acMode = document.getElementById('ac-mode');
                    if (data.ac_on === true) {
                        acEl.innerHTML = 'AC: <span class="text-green-500">🟢 PORNIT</span>';
                        acEl.className = 'text-xl font-bold glow-green';
                        acIcon.textContent = '❄️';
                        acMode.textContent = `Mod: ${data.ac_mode || '---'} | Fan: ${data.ac_fan || '---'} | Țintă: ${data.target_temp || '---'}°C`;
                    } else if (data.ac_on === false) {
                        acEl.innerHTML = 'AC: <span class="text-red-500">🔴 OPRIT</span>';
                        acEl.className = 'text-xl font-bold glow-red';
                        acIcon.textContent = '💤';
                        acMode.textContent = '';
                    } else {
                        acEl.innerHTML = 'AC: <span class="text-yellow-500">⚠️ Necunoscut</span>';
                        acEl.className = 'text-xl font-bold';
                        acIcon.textContent = '❓';
                        acMode.textContent = '';
                    }

                    // Metrici
                    document.getElementById('solar').textContent =
                        data.solar_production_kw != null ? data.solar_production_kw.toFixed(2) : '---';
                    document.getElementById('consum').textContent =
                        data.consumption_kw != null ? data.consumption_kw.toFixed(2) : '---';

                    const surplusEl = document.getElementById('surplus');
                    const surplusBar = document.getElementById('surplus-bar');
                    const surplusText = document.getElementById('surplus-text');
                    if (data.surplus_kw != null) {
                        const s = data.surplus_kw;
                        surplusEl.textContent = (s >= 0 ? '+' : '') + s.toFixed(2);
                        surplusEl.className = 'text-2xl font-bold ' + (s >= 0 ? 'text-green-500' : 'text-red-500');
                        // Bar vizual: 0-3kW range
                        const pct = Math.min(100, Math.max(0, (s / 3.0) * 100));
                        surplusBar.style.width = pct + '%';
                        surplusBar.className = 'h-4 rounded-full transition-all ' + (s >= 0 ? 'bg-green-500' : 'bg-red-500');
                        const prag = data.surplus_threshold || 1.4;
                        surplusText.textContent = `Prag: ${prag} kW`;
                    } else {
                        surplusEl.textContent = '---';
                        surplusEl.className = 'text-2xl font-bold text-slate-500';
                        surplusBar.style.width = '0%';
                    }

                    document.getElementById('battery').textContent =
                        data.battery_soc != null ? data.battery_soc.toFixed(0) : '---';
                    document.getElementById('temp-in').textContent =
                        data.indoor_temp != null ? data.indoor_temp.toFixed(1) : '---';
                    document.getElementById('temp-out').textContent =
                        data.outdoor_temp != null ? data.outdoor_temp.toFixed(1) : '---';

                    // Sursă
                    const srcMap = { 'modbus': '🟢 Modbus', 'cloud': '☁️ Cloud', 'local': '📡 Local' };
                    document.getElementById('source').textContent = srcMap[data.inverter_source] || data.inverter_source || '---';

                    // Decizie
                    const decMap = { 'turn_on': '🟢 PORNIRE', 'turn_off': '🔴 OPRIRE', 'none': '⚪ NICIUNA' };
                    document.getElementById('last-decision').textContent = decMap[data.last_decision] || data.last_decision || '---';
                    document.getElementById('last-reason').textContent = data.last_decision_reason || '';

                    // Setări
                    if (data.surplus_threshold) document.getElementById('set-surplus').value = data.surplus_threshold;
                    if (data.temp_threshold) document.getElementById('set-temp').value = data.temp_threshold;
                    if (data.hours_start != null) document.getElementById('set-start').value = data.hours_start;
                    if (data.hours_end != null) document.getElementById('set-end').value = data.hours_end;

                    // Timp
                    document.getElementById('update-time').textContent =
                        'Ultima actualizare: ' + new Date().toLocaleTimeString('ro-RO');

                    // Connection status
                    const connEl = document.getElementById('connection-status');
                    if (data.last_update) {
                        connEl.innerHTML = '<i class="fas fa-circle text-green-500 mr-1"></i>Conectat';
                    } else {
                        connEl.innerHTML = '<i class="fas fa-circle text-red-500 mr-1"></i>Deconectat';
                    }
                })
                .catch(err => {
                    console.error('Eroare fetch:', err);
                    document.getElementById('connection-status').innerHTML =
                        '<i class="fas fa-circle text-red-500 mr-1"></i>Eroare conexiune';
                });
        }

        function fetchLog() {
            fetch('/api/log')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('log-container');
                    if (data.logs && data.logs.length > 0) {
                        container.innerHTML = data.logs.map(l =>
                            '<div class="py-0.5 border-b border-slate-800 ' + l.level + '">' +
                            l.time + ' ' + l.message + '</div>'
                        ).join('');
                        container.scrollTop = container.scrollHeight;
                    }
                })
                .catch(() => {});
        }

        function manualOn() {
            fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'on'})
            }).then(() => fetchStatus());
        }

        function manualOff() {
            fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'off'})
            }).then(() => fetchStatus());
        }

        function manualAuto() {
            fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'auto'})
            }).then(() => fetchStatus());
        }

        function saveSettings() {
            const s = {
                surplus_threshold: parseFloat(document.getElementById('set-surplus').value),
                temp_threshold: parseFloat(document.getElementById('set-temp').value),
                hours_start: parseInt(document.getElementById('set-start').value),
                hours_end: parseInt(document.getElementById('set-end').value),
            };
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(s)
            }).then(r => r.json()).then(data => {
                alert(data.message || 'Setări salvate!');
                fetchStatus();
            });
        }

        // Auto-refresh la fiecare 10 secunde
        fetchStatus();
        fetchLog();
        autoRefresh = setInterval(() => { fetchStatus(); fetchLog(); }, 10000);
    </script>
</body>
</html>
"""


class WebServer:
    """Server Web pentru dashboard."""

    def __init__(self, controller):
        self.controller = controller
        self.app = None

    def run(self):
        """Pornește serverul web."""
        if not FLASK_AVAILABLE:
            logger.error("Flask nu e instalat. Rulează: pip install flask")
            return

        self.app = Flask(__name__)

        @self.app.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML)

        @self.app.route('/api/status')
        def api_status():
            return jsonify(self.controller.last_status)

        @self.app.route('/api/control', methods=['POST'])
        def api_control():
            data = request.get_json()
            action = data.get('action')
            if action == 'on':
                self.controller.set_manual_override('force_on')
            elif action == 'off':
                self.controller.set_manual_override('force_off')
            elif action == 'auto':
                self.controller.set_manual_override(None)
            return jsonify({'ok': True, 'action': action})

        @self.app.route('/api/settings', methods=['POST'])
        def api_settings():
            data = request.get_json()
            try:
                self.controller.update_settings(
                    surplus_threshold=data.get('surplus_threshold'),
                    temp_threshold=data.get('temp_threshold'),
                    hours_start=data.get('hours_start'),
                    hours_end=data.get('hours_end'),
                )
                return jsonify({'ok': True, 'message': 'Setări salvate cu succes'})
            except (ValueError, TypeError) as e:
                return jsonify({'ok': False, 'error': str(e)}), 400

        @self.app.route('/api/log')
        def api_log():
            try:
                with open(settings.LOG_FILE, 'r') as f:
                    lines = f.readlines()[-50:]
                logs = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    level = 'text-slate-400'
                    if 'WARNING' in line or 'warn' in line.lower():
                        level = 'text-amber-500'
                    elif 'ERROR' in line or 'error' in line.lower():
                        level = 'text-red-500'
                    parts = line.split(' ', 2)
                    time_str = parts[0] if parts else ''
                    msg = parts[-1] if len(parts) > 1 else line
                    logs.append({'time': time_str, 'message': msg, 'level': level})
                return jsonify({'logs': logs})
            except FileNotFoundError:
                return jsonify({'logs': []})

        logger.info(f"Web UI pornit pe http://0.0.0.0:{settings.WEB_PORT}")
        self.app.run(
            host=settings.WEB_HOST,
            port=settings.WEB_PORT,
            debug=False,
            use_reloader=False,
        )
