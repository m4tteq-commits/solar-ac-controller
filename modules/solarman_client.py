"""Client Solarman - citește producția și consumul de energie.

Strategie:
  1. Primar: Modbus TCP local pe stick-ul WiFi (port 8899)
  2. Fallback: API Cloud Solarman
"""
import logging
import time
import hashlib
import requests
from datetime import datetime

from config import settings

logger = logging.getLogger('solarman')


class SolarmanClient:
    """Comunicare cu invertorul Solarman (Modbus TCP local + API Cloud fallback)."""

    BASE_URL = "https://api.solarmanpv.com"

    def __init__(self):
        self.api_key = settings.SOLARMAN_API_KEY
        self.api_secret = settings.SOLARMAN_API_SECRET
        self.app_id = settings.SOLARMAN_APP_ID
        self.station_id = settings.SOLARMAN_STATION_ID
        self.stick_ip = settings.SOLARMAN_STICK_IP
        self.stick_port = settings.SOLARMAN_STICK_PORT
        self._session = requests.Session()
        self._token = None
        self._token_expiry = 0
        self._modbus_available = None  # None = necunt

    def _get_token(self):
        """Obține token de autentificare API."""
        if self._token and time.time() < self._token_expiry:
            return self._token

        try:
            url = f"{self.BASE_URL}/account/v1.0/token"
            params = {
                "appId": self.app_id,
                "language": "en",
            }
            timestamp = str(int(time.time() * 1000))
            sign_str = f"{self.api_key}{timestamp}{self.api_secret}"
            sign = hashlib.md5(sign_str.encode()).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Timestamp": timestamp,
                "Sign": sign,
            }

            resp = self._session.post(url, json=params, headers=headers, timeout=15)
            data = resp.json()

            if data.get("code") == "100000":
                self._token = data["data"]["accessToken"]
                self._token_expiry = time.time() + 3600  # 1 oră
                logger.info("Token Solarman obținut cu succes")
                return self._token
            else:
                logger.error(f"Eroare auth Solarman: {data}")
                return None

        except Exception as e:
            logger.error(f"Eroare obținere token Solarman: {e}")
            return None

    def get_live_data_modbus(self):
        """Citește date local prin Modbus TCP de pe stick-ul Solarman WiFi.

        Regiștrii Modbus pentru Sungrow/Solarman (LSW3 stick):
        - Inverter Power (generation): address 4990, 2 registrii (int32, kW * 100)
        - Total Load Power (consumption): address 4950, 2 registrii (int32, kW * 100)
        - Battery Power: address 4966, 2 registrii (int32, W, + charge / - discharge)
        - Battery SOC: address 4949, 1 registrii (%, * 10)
        - Grid Power: address 4979, 2 registrii (int32, W, + export / - import)
        """
        if not self.stick_ip:
            return None

        try:
            # Încearcă pysolarmanv5 (bibliotecă dedicată Solarman stick)
            import pysolarmanv5

            # Device SN - folosește primele 4 cifre din serial ca device ID
            device_sn = int(settings.SOLARMAN_INVERTER_SN[:4])
            modbus = pysolarmanv5.SolarmanV5(
                self.stick_ip,
                device_sn,
                port=self.stick_port,
                mb_slave_id=1,
                verbose=False,
            )

            # Regiștrii standard Sungrow/Solarman
            # Notă: adresele pot varia în funcție de modelul invertorului
            # Pentru SG04LP3 (Deye/Sungrow hybrid) cu LSW3 stick:

            # Generation Power (totale panouri) - 0.01W unit
            gen_raw = modbus.read_holding_registers(4990, 2)
            production_w = self._to_int32(gen_raw) if gen_raw else 0
            production_kw = abs(production_w) / 100.0 / 1000.0

            # Total Load Power (consum casă) - 0.01W unit
            load_raw = modbus.read_holding_registers(4950, 2)
            consumption_w = self._to_int32(load_raw) if load_raw else 0
            consumption_kw = abs(consumption_w) / 100.0 / 1000.0

            # Battery Power - 0.01W unit, + charge, - discharge
            batt_power_raw = modbus.read_holding_registers(4966, 2)
            battery_power_w = self._to_int32(batt_power_raw) if batt_power_raw else 0

            # Battery SOC - 0.1% unit
            batt_soc_raw = modbus.read_holding_registers(4949, 1)
            battery_soc = batt_soc_raw[0] / 10.0 if batt_soc_raw else 0

            # Grid Power - 0.01W unit, + export, - import
            grid_raw = modbus.read_holding_registers(4979, 2)
            grid_power_w = self._to_int32(grid_raw) if grid_raw else 0

            modbus.disconnect()

            data = {
                'production_kw': round(production_kw, 2),
                'consumption_kw': round(consumption_kw, 2),
                'battery_soc': round(battery_soc, 1),
                'battery_power_w': battery_power_w / 100.0,  # + charge / - discharge
                'grid_power_w': grid_power_w / 100.0,        # + export / - import
                'battery_charging': battery_power_w > 0,
                'source': 'modbus',
                'timestamp': datetime.now().isoformat(),
            }

            logger.debug(
                f"Modbus OK: prod={production_kw:.2f}kW, "
                f"cons={consumption_kw:.2f}kW, bat={battery_soc:.1f}%"
            )
            return data

        except ImportError:
            if self._modbus_available is None:
                logger.warning(
                    "pysolarmanv5 neinstalat. "
                    "Instalează cu: pip install pysolarmanv5"
                )
                self._modbus_available = False
            return None
        except Exception as e:
            logger.debug(f"Modbus indisponibil: {e}")
            self._modbus_available = False
            return None

    @staticmethod
    def _to_int32(registers):
        """Convertește 2 registrii Modbus în int32."""
        if not registers or len(registers) < 2:
            return 0
        value = (registers[0] << 16) | registers[1]
        if value >= 0x80000000:
            value -= 0x100000000
        return value

    def get_live_data_cloud(self):
        """Citește date live din API-ul cloud Solarman."""
        try:
            token = self._get_token()
            if not token:
                return None

            url = f"{self.BASE_URL}/device/v1.0/currentData"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            params = {
                "deviceSn": settings.SOLARMAN_INVERTER_SN,
            }

            resp = self._session.get(url, params=params, headers=headers, timeout=15)
            data = resp.json()

            if data.get("code") == "100000" and data.get("data"):
                device_data = data["data"]
                return {
                    'production_kw': float(device_data.get('generationPower', 0)) / 1000,
                    'consumption_kw': float(device_data.get('usePower', 0)) / 1000,
                    'battery_soc': float(device_data.get('batterySoc', 0)),
                    'battery_power_w': float(device_data.get('batteryPower', 0)),
                    'grid_power_w': float(device_data.get('gridPower', 0)),
                    'battery_charging': float(device_data.get('batteryPower', 0)) > 0,
                    'source': 'cloud',
                    'timestamp': datetime.now().isoformat(),
                }
            else:
                logger.warning(f"Răspuns Solarman neașteptat: {data}")
                return None

        except Exception as e:
            logger.error(f"Eroare citire Solarman cloud: {e}")
            return None

    def get_live_data(self):
        """Citește date live - întâi Modbus local, apoi cloud."""
        # Încearcă Modbus local (fără consum API)
        if self.stick_ip:
            data = self.get_live_data_modbus()
            if data:
                return data

        # Fallback la cloud
        return self.get_live_data_cloud()
