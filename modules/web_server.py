"""Web UI - Dashboard în limba română."""
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
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; color: #e2e8f0; min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1e3a5f, #0f172a);
            padding: 20px; text-align: center;
            border-bottom: 2px solid #f59e0b;
        }
        .header h1 { color: #f59e0b; font-size: 1.8em; }
        .header p { color: #94a3b8; margin-top: 5px; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .card {
            background: #1e293b; border-radius: 12px; padding: 20px;
            border: 1px solid #334155; text-align: center;
        }
        .card .label { color: #94a3b8; font-size: 0.85em; margin-bottom: 8px; }
        .card .value { font-size: 1.8em; font-weight: bold; }
        .card .unit { color: #64748b; font-size: 0.75em; }
        .solar { color: #f59e0b; }
        .consum { color: #f97316; }
        .surplus-pos { color: #22c55e; }
        .surplus-neg { color: #ef4444; }
        .temp { color: #38bdf8; }
        .battery { color: #a78bfa; }
        .ac-on { color: #22c55e; }
        .ac-off { color: #ef4444; }
        .status-bar {
            background: #1e293b; border-radius: 12px; padding: 15px 20px;
            margin: 15px 0; border: 1px solid #334155;
            display: flex; justify-content: space-between; align-items: center;
        }
        .status-text { font-size: 0.9em; color: #94a3b8; }
        .status-text strong { color: #e2e8f0; }
        .btn {
            display: inline-block; padding: 10px 20px; border-radius: 8px;
            border: none; cursor: pointer; font-size: 0.9em; font-weight: 600;
            margin: 5px; transition: all 0.2s;
        }
        .btn-on { background: #22c55e; color: #000; }
        .btn-off { background: #ef4444; color: #fff; }
        .btn-auto { background: #3b82f6; color: #fff; }
        .btn:hover { transform: scale(1.05); opacity: 0.9; }
        .settings {
            background: #1e293b; border-radius: 12px; padding: 20px;
            margin: 15px 0; border: 1px solid #334155;
        }
        .settings h3 { color: #f59e0b; margin-bottom: 15px; }
        .settings label { display: block; margin: 10px 0 5px; color: #94a3b8; font-size: 0.85em; }
        .settings input {
            width: 100%; padding: 8px 12px; border-radius: 6px;
            border: 1px solid #334155; background: #0f172a; color: #e2e8f0;
        }
        .settings .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .btn-save { background: #f59e0b; color: #000; margin-top: 15px; }
        .log {
            background: #0f172a; border-radius: 12px; padding: 15px;
            margin: 15px 0; border: 1px solid #334155;
            max-height: 200px; overflow-y: auto; font-family: monospace;
            font-size: 0.8em; color: #64748b;
        }
        .log-entry { padding: 2px 0; border-bottom: 1px solid #1e293b; }
        .log-entry.info { color: #94a3b8; }
        .log-entry.warn { color: #f59e0b; }
        .log-entry.error { color: #ef4444; }
        .update-time { text-align: center; color: #64748b; font-size: 0.8em; margin-top: 10px; }
        @media (max-width: 600px) {
            .grid { grid-template-columns: 1fr 1fr; }
            .settings .row { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>☀️ Solar AC Controller</h1>
        <p>Automatizare aer condiționat bazată pe energie solară</p>
    </div>

    <div class="container">
        <!-- Stare AC -->
        <div class="status-bar">
            <div>
                <span style="font-size: 1.2em;" id="ac-status">❄️ AC: ---</span>
            </div>
            <div>
                <button class="btn btn-on" onclick="manualOn()">Pornește</button>
                <button class="btn btn-off" onclick="manualOff()">Oprește</button>
                <button class="btn btn-auto" onclick="manualAuto()">Auto</button>
            </div>
        </div>

        <!-- Metrici -->
        <div class="grid">
            <div class="card">
                <div class="label">☀️ Producție solară</div>
                <div class="value solar" id="solar">---</div>
                <div class="unit">kW</div>
            </div>
            <div class="card">
                <div class="label">🏠 Consum casă</div>
                <div class="value consum" id="consum">---</div>
                <div class="unit">kW</div>
            </div>
            <div class="card">
                <div class="label">📊 Surplus</div>
                <div class="value" id="surplus">---</div>
                <div class="unit">kW</div>
            </div>
            <div class="card">
                <div class="label">🔋 Baterie</div>
                <div class="value battery" id="battery">---</div>
                <div class="unit">%</div>
            </div>
            <div class="card">
                <div class="label">🌡️ T° interior</div>
                <div class="value temp" id="temp-in">---</div>
                <div class="unit">°C</div>
            </div>
            <div class="card">
                <div class="label">🌤° T° exterior</div>
                <div class="value temp" id="temp-out">---</div>
                <div class="unit">°C</div>
            </div>
        </div>

        <!-- Ultima decizie -->
        <div class="status-bar">
            <div class="status-text">
                📋 <strong>Ultima decizie:</strong> <span id="last-decision">---</span>
            </div>
            <div class="status-text" id="last-reason">---</div>
        </div>

        <!-- Setări -->
        <div class="settings">
            <h3>⚙️ Setări</h3>
            <div class="row">
                <div>
                    <label>Prag surplus (kW)</label>
                    <input type="number" id="set-surplus" step="0.1" value="1.4">
                </div>
                <div>
                    <label>Prag temperatură (°C)</label>
                    <input type="number" id="set-temp" step="0.5" value="24">
                </div>
            </div>
            <div class="row">
                <div>
                    <label>Ora pornire</label>
                    <input type="number" id="set-start" min="0" max="23" value="8">
                </div>
                <div>
                    <label>Ora oprire</label>
                    <input type="number" id="set-end" min="0" max="23" value="22">
                </div>
            </div>
            <button class="btn btn-save" onclick="saveSettings()">💎 Salvează setările</button>
        </div>

        <!-- Log -->
        <div class="settings">
            <h3>📜 Jurnal</h3>
            <div class="log" id="log-container">
                <div class="log-entry info">Se încarcă...</div>
            </div>
        </div>

        <div class="update-time" id="update-time">Ultima actualizare: ---</div>
    </div>

    <script>
        let autoRefresh;

        function fetchStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    // AC status
                    const acEl = document.getElementById('ac-status');
                    if (data.ac_on === true) {
                        acEl.innerHTML = '❄️ AC: <span class="ac-on">🟢 PORNIT</span>';
                    } else if (data.ac_on === false) {
                        acEl.innerHTML = '❄️ AC: <span class="ac-off">🔴 OPRIT</span>';
                    } else {
                        acEl.innerHTML = '❄️ AC: ⚠️ Necunoscut';
                    }

                    // Metrici
                    document.getElementById('solar').textContent =
                        data.solar_production_kw !== null ? data.solar_production_kw.toFixed(2) : '---';
                    document.getElementById('consum').textContent =
                        data.consumption_kw !== null ? data.consumption_kw.toFixed(2) : '---';

                    const surplusEl = document.getElementById('surplus');
                    if (data.surplus_kw !== null) {
                        surplusEl.textContent = (data.surplus_kw >= 0 ? '+' : '') + data.surplus_kw.toFixed(2);
                        surplusEl.className = 'value ' + (data.surplus_kw >= 0 ? 'surplus-pos' : 'surplus-neg');
                    } else {
                        surplusEl.textContent = '---';
                    }

                    document.getElementById('battery').textContent =
                        data.battery_soc !== null ? data.battery_soc.toFixed(0) : '---';
                    document.getElementById('temp-in').textContent =
                        data.indoor_temp !== null ? data.indoor_temp.toFixed(1) : '---';
                    document.getElementById('temp-out').textContent =
                        data.outdoor_temp !== null ? data.outdoor_temp.toFixed(1) : '---';

                    // Decizie
                    document.getElementById('last-decision').textContent = data.last_decision || '---';
                    document.getElementById('last-reason').textContent = data.last_decision_reason || '';

                    // Setări
                    document.getElementById('set-surplus').value = data.surplus_threshold || 1.4;
                    document.getElementById('set-temp').value = data.temp_threshold || 24;
                    document.getElementById('set-start').value = data.hours_start || 8;
                    document.getElementById('set-end').value = data.hours_end || 22;

                    // Timp
                    document.getElementById('update-time').textContent =
                        'Ultima actualizare: ' + new Date().toLocaleTimeString('ro-RO');
                })
                .catch(err => console.error('Eroare fetch:', err));
        }

        function fetchLog() {
            fetch('/api/log')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('log-container');
                    if (data.logs && data.logs.length > 0) {
                        container.innerHTML = data.logs.map(l =>
                            '<div class="log-entry ' + l.level + '">' +
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
            const settings = {
                surplus_threshold: parseFloat(document.getElementById('set-surplus').value),
                temp_threshold: parseFloat(document.getElementById('set-temp').value),
                hours_start: parseInt(document.getElementById('set-start').value),
                hours_end: parseInt(document.getElementById('set-end').value),
            };
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings)
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
                self.controller.last_status['manual_override'] = 'force_on'
            elif action == 'off':
                self.controller.last_status['manual_override'] = 'force_off'
            elif action == 'auto':
                self.controller.last_status['manual_override'] = None
            return jsonify({'ok': True, 'action': action})

        @self.app.route('/api/settings', methods=['POST'])
        def api_settings():
            data = request.get_json()
            try:
                if 'surplus_threshold' in data:
                    settings.SURPLUS_THRESHOLD_KW = float(data['surplus_threshold'])
                    self.controller.last_status['surplus_threshold'] = settings.SURPLUS_THRESHOLD_KW
                if 'temp_threshold' in data:
                    settings.TEMP_THRESHOLD = float(data['temp_threshold'])
                    self.controller.last_status['temp_threshold'] = settings.TEMP_THRESHOLD
                if 'hours_start' in data:
                    settings.ALLOWED_HOURS_START = int(data['hours_start'])
                    self.controller.last_status['hours_start'] = settings.ALLOWED_HOURS_START
                if 'hours_end' in data:
                    settings.ALLOWED_HOURS_END = int(data['hours_end'])
                    self.controller.last_status['hours_end'] = settings.ALLOWED_HOURS_END
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
                    level = 'info'
                    if 'WARNING' in line or 'warn' in line.lower():
                        level = 'warn'
                    elif 'ERROR' in line or 'error' in line.lower():
                        level = 'error'
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
