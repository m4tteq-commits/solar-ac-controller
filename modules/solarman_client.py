"""Client API Solarman - citește producția și consumul de energie."""
import logging
import time
import hashlib
import requests

from config import settings

logger = logging.getLogger('solarman')


class SolarmanClient:
    """Comunicare cu invertorul Solarman (API Cloud + fallback local)."""

    BASE_URL = "https://api.solarmanpv.com"

    def __init__(self):
        self.api_key = settings.SOLARMAN_API_KEY
        self.api_secret = settings.SOLARMAN_API_SECRET
        self.app_id = settings.SOLARMAN_APP_ID
        self.station_id = settings.SOLARMAN_STATION_ID
        self.stick_ip = settings.SOLARMAN_STICK_IP
        self._session = requests.Session()
        self._token = None
        self._token_expiry = 0

    def _get_token(self):
        """Obține token de autentificare API."""
        if self._token and time.time() < self._token_expiry:
            return self._token

        try:
            # Solarman API v2 - autentificare
            url = f"{self.BASE_URL}/account/v1.0/token"
            params = {
                "appId": self.app_id,
                "language": "en",
            }
            # Semnătură HMAC
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
                    'grid_export_kw': float(device_data.get('gridPower', 0)) / 1000,
                    'solar_to_home_kw': float(device_data.get('homePower', 0)) / 1000,
                    'solar_to_battery_kw': float(device_data.get('batteryPower', 0)) / 1000,
                    'solar_to_grid_kw': float(device_data.get('gridPower', 0)) / 1000,
                    'source': 'cloud',
                }
            else:
                logger.warning(f"Răspuns Solarman neașteptat: {data}")
                return None

        except Exception as e:
            logger.error(f"Eroare citire Solarman cloud: {e}")
            return None

    def get_live_data_local(self):
        """Citește date local de pe stick-ul Solarman WiFi."""
        if not self.stick_ip:
            return None

        try:
            # Solarman stick local API (port 8899 sau HTTP)
            url = f"http://{self.stick_ip}/status"
            resp = self._session.get(url, timeout=10)
            data = resp.json()

            return {
                'production_kw': float(data.get('Power', 0)) / 1000,
                'consumption_kw': float(data.get('Consumption', 0)) / 1000,
                'battery_soc': float(data.get('BatterySOC', 0)),
                'grid_export_kw': float(data.get('GridPower', 0)) / 1000,
                'solar_to_home_kw': float(data.get('HomePower', 0)) / 1000,
                'solar_to_battery_kw': float(data.get('BatteryPower', 0)) / 1000,
                'solar_to_grid_kw': float(data.get('GridPower', 0)) / 1000,
                'source': 'local',
            }
        except Exception as e:
            logger.debug(f"Solarman local indisponibil: {e}")
            return None

    def get_live_data(self):
        """Citește date live - întâi local, apoi cloud."""
        # Încearcă local (fără consum API)
        if self.stick_ip:
            data = self.get_live_data_local()
            if data:
                return data

        # Fallback la cloud
        return self.get_live_data_cloud()
