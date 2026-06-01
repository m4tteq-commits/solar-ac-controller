"""
Solar AC Controller - Principal
Automatizare AC bazată pe surplus energie solară
"""
import sys
import signal
import logging
import threading
from datetime import datetime

from config import settings
from modules.solarman_client import SolarmanClient
from modules.midea_client import MideaClient
from modules.decision_engine import DecisionEngine
from modules.email_notifier import EmailNotifier
from modules.telegram_bot import TelegramBot
from modules.web_server import WebServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/anne/solar-ac-controller/solar-ac.log'),
    ]
)
logger = logging.getLogger('main')


class SolarACController:
    def __init__(self):
        self.running = True
        self.solarman = SolarmanClient()
        self.midea = MideaClient()
        self.engine = DecisionEngine()
        self.emailer = EmailNotifier()
        self.telegram = TelegramBot(self)
        self.web = WebServer(self)
        self.last_status = {
            'ac_on': None,
            'solar_production_kw': None,
            'consumption_kw': None,
            'surplus_kw': None,
            'indoor_temp': None,
            'outdoor_temp': None,
            'target_temp': settings.TARGET_TEMP,
            'last_decision': None,
            'last_decision_time': None,
            'surplus_threshold': settings.SURPLUS_THRESHOLD_KW,
            'temp_threshold': settings.TEMP_THRESHOLD,
            'hours_start': settings.ALLOWED_HOURS_START,
            'hours_end': settings.ALLOWED_HOURS_END,
            'manual_override': None,
        }

    def tick(self):
        """Execută o singură iterație de verificare."""
        try:
            now = datetime.now()
            logger.info(f"--- Verificare {now.strftime('%H:%M:%S')} ---")

            # 1. Citește date solar
            solar = self.solarman.get_live_data()
            if solar is None:
                logger.warning("Nu am putut citi datele Solarman")
                return

            self.last_status['solar_production_kw'] = solar['production_kw']
            self.last_status['consumption_kw'] = solar['consumption_kw']
            surplus = solar['production_kw'] - solar['consumption_kw']
            self.last_status['surplus_kw'] = round(surplus, 2)
            self.last_status['battery_soc'] = solar.get('battery_soc')
            self.last_status['grid_export_kw'] = solar.get('grid_export_kw')
            self.last_status['solar_to_home_kw'] = solar.get('solar_to_home_kw')
            self.last_status['solar_to_battery_kw'] = solar.get('solar_to_battery_kw')
            self.last_status['solar_to_grid_kw'] = solar.get('solar_to_grid_kw')

            logger.info(
                f"Solar: {solar['production_kw']:.2f} kW | "
                f"Consum: {solar['consumption_kw']:.2f} kW | "
                f"Surplus: {surplus:.2f} kW | "
                f"Baterie: {solar.get('battery_soc', '?')}%"
            )

            # 2. Citește stare AC și temperatură
            ac_state = self.midea.get_state()
            if ac_state:
                self.last_status['ac_on'] = ac_state.get('is_on', False)
                self.last_status['indoor_temp'] = ac_state.get('indoor_temp')
                self.last_status['outdoor_temp'] = ac_state.get('outdoor_temp')
                self.last_status['ac_mode'] = ac_state.get('mode')
                self.last_status['ac_target_temp'] = ac_state.get('target_temp')
                self.last_status['ac_fan_speed'] = ac_state.get('fan_speed')
                logger.info(
                    f"AC: {'PORNIT' if ac_state.get('is_on') else 'OPRIT'} | "
                    f"T int: {ac_state.get('indoor_temp')}°C | "
                    f"T ext: {ac_state.get('outdoor_temp')}°C"
                )

            # 3. Decizie
            decision = self.engine.decide(surplus, self.last_status, now)
            self.last_status['last_decision'] = decision['action']
            self.last_status['last_decision_time'] = now.isoformat()
            self.last_status['last_decision_reason'] = decision['reason']
            logger.info(f"Decizie: {decision['action']} — {decision['reason']}")

            # 4. Execută decizia
            if decision['action'] == 'turn_on' and not self.last_status.get('ac_on'):
                logger.info(">>> Pornesc AC-ul")
                self.midea.turn_on(
                    temp=settings.TARGET_TEMP,
                    mode='cool',
                    fan_speed='auto'
                )
                self.emailer.send_notification(
                    "🔵 AC Pornit automat",
                    f"Solar AC Controller a pornit aerul condiționat.\n\n"
                    f"Motiv: {decision['reason']}\n"
                    f"Surplus: {surplus:.2f} kW\n"
                    f"Producție: {solar['production_kw']:.2f} kW\n"
                    f"Consum casă: {solar['consumption_kw']:.2f} kW\n"
                    f"T. interior: {self.last_status.get('indoor_temp', '?')}°C\n"
                    f"T. țintă: {settings.TARGET_TEMP}°C\n"
                    f"Ora: {now.strftime('%H:%M:%S')}\n"
                    f"Baterie: {solar.get('battery_soc', '?')}%"
                )
                self.telegram.send_status_msg(
                    f"🔵 AC PORNICIONAT\n"
                    f"{decision['reason']}\n"
                    f"Surplus: {surplus:.2f} kW | T°: {self.last_status.get('indoor_temp', '?')}°C"
                )

            elif decision['action'] == 'turn_off' and self.last_status.get('ac_on'):
                logger.info(">>> Opresc AC-ul")
                self.midea.turn_off()
                self.emailer.send_notification(
                    "🔴 AC Oprit automat",
                    f"Solar AC Controller a oprit aerul condiționat.\n\n"
                    f"Motiv: {decision['reason']}\n"
                    f"Surplus: {surplus:.2f} kW\n"
                    f"Producție: {solar['production_kw']:.2f} kW\n"
                    f"Consum casă: {solar['consumption_kw']:.2f} kW\n"
                    f"Ora: {now.strftime('%H:%M:%S')}"
                )
                self.telegram.send_status_msg(
                    f"🔴 AC OPRIIT\n"
                    f"{decision['reason']}\n"
                    f"Surplus: {surplus:.2f} kW"
                )

        except Exception as e:
            logger.exception(f"Eroare în tick: {e}")

    def run(self):
        """Bucla principală."""
        logger.info("=" * 50)
        logger.info("Solar AC Controller - Pornire")
        logger.info("=" * 50)

        # Pornește botul Telegram în thread separat
        tg_thread = threading.Thread(target=self.telegram.run, daemon=True)
        tg_thread.start()

        # Pornește Web UI în thread separat
        web_thread = threading.Thread(target=self.web.run, daemon=True)
        web_thread.start()

        import schedule
        import time

        schedule.every(settings.CHECK_INTERVAL_SECONDS).seconds.do(self.tick)

        # Prima verificare imediată
        self.tick()

        logger.info(f"Ciclul de verificare la fiecare {settings.CHECK_INTERVAL_SECONDS}s")
        logger.info(f"Prag surplus: {settings.SURPLUS_THRESHOLD_KW} kW")
        logger.info(f"Temp prag: {settings.TEMP_THRESHOLD}°C")
        logger.info(f"Ore: {settings.ALLOWED_HOURS_START}:00 - {settings.ALLOWED_HOURS_END}:00")

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.running = False
        self.telegram.stop()


def main():
    controller = SolarACController()

    def signal_handler(sig, frame):
        logger.info("Oprire sistem...")
        controller.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    controller.run()


if __name__ == '__main__':
    main()
