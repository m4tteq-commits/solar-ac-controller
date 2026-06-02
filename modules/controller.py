"""Controller principal - orchestrează toate modulele.

Rulează bucla principală de automatizare la fiecare CHECK_INTERVAL_SECONDS.
"""
import logging
import threading
import time
from datetime import datetime

from config import settings
from modules.solarman_client import SolarmanClient
from modules.midea_client import MideaController
from modules.decision_engine import DecisionEngine
from modules.email_notifier import EmailNotifier
from modules.telegram_bot import TelegramBot
from modules.web_server import WebServer

logger = logging.getLogger('controller')


class SolarACController:
    """Controller principal al sistemului Solar AC."""

    def __init__(self):
        self.inverter = SolarmanClient()
        self.ac = MideaController()
        self.engine = DecisionEngine()
        self.emailer = EmailNotifier()
        self.telegram = TelegramBot(self)
        self.web = WebServer(self)

        # Stare partajată între module
        self.last_status = {
            'solar_production_kw': None,
            'consumption_kw': None,
            'surplus_kw': None,
            'battery_soc': None,
            'battery_power_w': None,
            'battery_charging': None,
            'grid_power_w': None,
            'indoor_temp': None,
            'outdoor_temp': None,
            'target_temp': None,
            'ac_on': None,
            'ac_mode': None,
            'ac_fan': None,
            'last_decision': 'Inițializare',
            'last_decision_reason': 'Sistemul tocmai a pornit',
            'last_decision_time': None,
            'manual_override': None,
            'surplus_threshold': settings.SURPLUS_THRESHOLD_KW,
            'temp_threshold': settings.TEMP_THRESHOLD,
            'hours_start': settings.ALLOWED_HOURS_START,
            'hours_end': settings.ALLOWED_HOURS_END,
            'inverter_source': None,
            'last_update': None,
        }

        self._running = False
        self._manual_override = None  # None | 'force_on' | 'force_off'

    def start(self):
        """Pornește controllerul."""
        logger.info("=" * 60)
        logger.info("Solar AC Controller - Pornire")
        logger.info("=" * 60)

        self._running = True

        # Pornește Telegram bot într-un thread separat
        if self.telegram.token and self.telegram.token != "AICI_PUNE_BOT_TOKEN":
            tg_thread = threading.Thread(target=self.telegram.run, daemon=True)
            tg_thread.start()
            logger.info("Bot Telegram pornit în fundal")

        # Pornește Web UI într-un thread separat
        web_thread = threading.Thread(target=self.web.run, daemon=True)
        web_thread.start()
        logger.info(f"Web UI pornit pe portul {settings.WEB_PORT}")

        # Bucla principală de automatizare
        logger.info(f"Bucla de automatizare: verificare la fiecare {settings.CHECK_INTERVAL_SECONDS}s")
        self._main_loop()

    def stop(self):
        """Oprește controllerul."""
        logger.info("Oprire Solar AC Controller...")
        self._running = False
        self.telegram.stop()

    def _main_loop(self):
        """Bucla principală de automatizare."""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Eroare în bucla principală: {e}", exc_info=True)

            # Așteaptă până la următoarea verificare
            for _ in range(settings.CHECK_INTERVAL_SECONDS):
                if not self._running:
                    break
                time.sleep(1)

    def _tick(self):
        """O iterație a buclei de automatizare."""
        now = datetime.now()

        # 1. Citește datele de la invertor
        inverter_data = self.inverter.get_live_data()
        if inverter_data:
            self.last_status['solar_production_kw'] = inverter_data.get('production_kw')
            self.last_status['consumption_kw'] = inverter_data.get('consumption_kw')
            self.last_status['battery_soc'] = inverter_data.get('battery_soc')
            self.last_status['battery_power_w'] = inverter_data.get('battery_power_w')
            self.last_status['battery_charging'] = inverter_data.get('battery_charging')
            self.last_status['grid_power_w'] = inverter_data.get('grid_power_w')
            self.last_status['inverter_source'] = inverter_data.get('source')

            # Calculează surplus
            production = inverter_data.get('production_kw', 0) or 0
            consumption = inverter_data.get('consumption_kw', 0) or 0
            self.last_status['surplus_kw'] = round(production - consumption, 2)
        else:
            logger.warning("Nu am putut citi datele de la invertor!")
            self.emailer.send_notification(
                "⚠️ Conexiune invertor pierdută",
                f"Nu am putut citi datele de la invertor la {now.strftime('%H:%M:%S')}.\n"
                f"Verifică conexiunea la rețea și starea stick-ului Solarman."
            )

        # 2. Citește starea AC-ului
        ac_state = self.ac.get_state()
        if ac_state:
            self.last_status['indoor_temp'] = ac_state.get('indoor_temp')
            self.last_status['outdoor_temp'] = ac_state.get('outdoor_temp')
            self.last_status['target_temp'] = ac_state.get('target_temp')
            self.last_status['ac_on'] = ac_state.get('is_on')
            self.last_status['ac_mode'] = ac_state.get('mode')
            self.last_status['ac_fan'] = ac_state.get('fan_speed')
            # Sincronizează starea motorului de decizie
            self.engine._ac_on = ac_state.get('is_on', False)

        # 3. Override manual
        self.last_status['manual_override'] = self._manual_override

        # 4. Ia decizie
        surplus = self.last_status.get('surplus_kw') or 0
        indoor_temp = self.last_status.get('indoor_temp')

        if self._manual_override == 'force_on':
            if not self.engine.ac_on:
                decision = {'action': 'turn_on', 'reason': 'Override manual: forțat pornit'}
            else:
                decision = {'action': 'none', 'reason': 'Override manual: forțat pornit'}
        elif self._manual_override == 'force_off':
            if self.engine.ac_on:
                decision = {'action': 'turn_off', 'reason': 'Override manual: forțat oprit'}
            else:
                decision = {'action': 'none', 'reason': 'Override manual: forțat oprit'}
        else:
            decision = self.engine.decide(surplus, indoor_temp)

        self.last_status['last_decision'] = decision['action']
        self.last_status['last_decision_reason'] = decision['reason']
        self.last_status['last_decision_time'] = now.strftime('%H:%M:%S')
        self.last_status['last_update'] = now.strftime('%H:%M:%S')

        # 5. Execută decizia
        if decision['action'] == 'turn_on':
            success = self.ac.turn_on()
            if success:
                self.emailer.send_notification(
                    "❄️ AC PORNIT (automat)",
                    f"Aerul condiționat a fost pornit automat.\n\n"
                    f"Motiv: {decision['reason']}\n"
                    f"Surplus: {surplus:.2f} kW\n"
                    f"T° interior: {indoor_temp}°C\n"
                    f"Ora: {now.strftime('%H:%M:%S')}"
                )
                self.telegram.send_status_msg(
                    f"❄️ AC PORNIT automat\n"
                    f"📊 Surplus: {surplus:.2f} kW\n"
                    f"🌡️ T°: {indoor_temp}°C\n"
                    f"📋 {decision['reason']}"
                )
        elif decision['action'] == 'turn_off':
            success = self.ac.turn_off()
            if success:
                self.emailer.send_notification(
                    "🔴 AC OPRIT (automat)",
                    f"Aerul condiționat a fost oprit automat.\n\n"
                    f"Motiv: {decision['reason']}\n"
                    f"Surplus: {surplus:.2f} kW\n"
                    f"Ora: {now.strftime('%H:%M:%S')}"
                )
                self.telegram.send_status_msg(
                    f"🔴 AC OPRIT automat\n"
                    f"📊 Surplus: {surplus:.2f} kW\n"
                    f"📋 {decision['reason']}"
                )

        # Log periodic (la fiecare tick)
        logger.info(
            f"Status: solar={self.last_status['solar_production_kw']}kW, "
            f"cons={self.last_status['consumption_kw']}kW, "
            f"surplus={self.last_status['surplus_kw']}kW, "
            f"bat={self.last_status['battery_soc']}%, "
            f"T°in={self.last_status['indoor_temp']}°C, "
            f"AC={'ON' if self.last_status['ac_on'] else 'OFF'}, "
            f"decizie={decision['action']}"
        )

    def set_manual_override(self, mode):
        """Setează modul manual.

        Args:
            mode: 'force_on', 'force_off', sau None pentru automat
        """
        self._manual_override = mode
        logger.info(f"Override manual setat: {mode}")

    def update_settings(self, surplus_threshold=None, temp_threshold=None,
                        hours_start=None, hours_end=None):
        """Actualizează setările din runtime."""
        if surplus_threshold is not None:
            settings.SURPLUS_THRESHOLD_KW = float(surplus_threshold)
            self.last_status['surplus_threshold'] = settings.SURPLUS_THRESHOLD_KW
        if temp_threshold is not None:
            settings.TEMP_THRESHOLD = float(temp_threshold)
            self.last_status['temp_threshold'] = settings.TEMP_THRESHOLD
        if hours_start is not None:
            settings.ALLOWED_HOURS_START = int(hours_start)
            self.last_status['hours_start'] = settings.ALLOWED_HOURS_START
        if hours_end is not None:
            settings.ALLOWED_HOURS_END = int(hours_end)
            self.last_status['hours_end'] = settings.ALLOWED_HOURS_END
        logger.info(
            f"Setări actualizate: surplus={settings.SURPLUS_THRESHOLD_KW}kW, "
            f"temp={settings.TEMP_THRESHOLD}°C, "
            f"ore={settings.ALLOWED_HOURS_START}:00-{settings.ALLOWED_HOURS_END}:00"
        )
