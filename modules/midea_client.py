"""Client Midea AC - control local prin rețea WiFi.

Folosește biblioteca msmart-ng (midea-local) pentru control local.
"""
import logging
import socket
from datetime import datetime

from config import settings

logger = logging.getLogger('midea')


class MideaController:
    """Comunicare locală cu AC-ul Midea prin protocolul midea-lan."""

    MIDEA_PORT = 6444

    # Moduri
    MODES = {
        'auto': 0x00,
        'cool': 0x01,
        'dry': 0x02,
        'fan': 0x03,
        'heat': 0x04,
    }

    def __init__(self):
        self.device_id = settings.MIDEA_DEVICE_ID
        self.local_key = settings.MIDEA_LOCAL_KEY
        self.device_ip = settings.MIDEA_IP
        self._use_library = False
        self._device_info = None

        # Încearcă să folosești biblioteca msmart-ng (mai robustă)
        try:
            from msmart.device import AirConditioningDevice
            from msmart.discover import discover
            self._use_library = True
            self._lib_discover = discover
            self._lib_device_class = AirConditioningDevice
            logger.info("Biblioteca msmart-ng disponibilă")
        except ImportError:
            logger.warning(
                "Biblioteca msmart-ng nu e instalată. "
                "Instalează cu: pip install msmart-ng"
            )

    def _discover_device(self):
        """Descoperă dispozitivul Midea pe rețea."""
        if not self._use_library:
            return None

        try:
            devices = self._lib_discover()
            for dev in devices:
                if str(dev.id) == self.device_id or (self.device_ip and self.device_ip == dev.ip):
                    self._device_info = dev
                    return dev
            return None
        except Exception as e:
            logger.error(f"Eroare descoperire Midea: {e}")
            return None

    def get_state(self):
        """Citește starea actuală a AC-ului.

        Returns:
            dict cu: is_on, indoor_temp, outdoor_temp, target_temp, mode, fan_speed
            sau None dacă nu se poate citi.
        """
        if self._use_library:
            try:
                device_info = self._discover_device()
                if not device_info:
                    logger.warning("Dispozitivul Midea nu a fost găsit pe rețea")
                    return None

                dev = self._lib_device_class(
                    device_ip=device_info.ip,
                    device_id=int(device_info.id),
                    device_type=settings.MIDEA_DEVICE_TYPE,
                )
                dev.refresh()

                return {
                    'is_on': dev.power_state,
                    'indoor_temp': dev.indoor_temperature,
                    'outdoor_temp': dev.outdoor_temperature,
                    'target_temp': dev.target_temperature,
                    'mode': dev.mode_name if hasattr(dev, 'mode_name') else 'unknown',
                    'fan_speed': dev.fan_speed if hasattr(dev, 'fan_speed') else 'unknown',
                    'timestamp': datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error(f"Eroare citire stare Midea: {e}")
                return None

        # Fallback - nu se poate citi fără bibliotecă
        logger.debug("Midea: bibliotecă indisponibilă, nu pot citi starea")
        return None

    def turn_on(self, temp=None, mode='cool', fan_speed='auto'):
        """Pornește AC-ul.

        Args:
            temp: Temperatura țintă (°C). Default din settings.
            mode: Modul de funcționare ('cool', 'auto', 'dry', 'fan', 'heat').
            fan_speed: Viteza ventilatorului ('auto', 'low', 'medium', 'high').
        """
        if temp is None:
            temp = settings.TARGET_TEMP

        logger.info(f"Pornesc Midea AC: {temp}°C, mod {mode}, fan {fan_speed}")

        if self._use_library:
            try:
                device_info = self._discover_device()
                if device_info:
                    dev = self._lib_device_class(
                        device_ip=device_info.ip,
                        device_id=int(device_info.id),
                        device_type=settings.MIDEA_DEVICE_TYPE,
                    )
                    dev.refresh()
                    dev.power_state = True
                    dev.mode = self.MODES.get(mode, 0x01)
                    dev.target_temperature = temp
                    dev.apply()
                    logger.info("Midea AC pornit cu succes")
                    return True
            except Exception as e:
                logger.error(f"Eroare pornire Midea: {e}")

        logger.warning("Nu am putut porni AC-ul Midea (bibliotecă indisponibilă)")
        return False

    def turn_off(self):
        """Oprește AC-ul."""
        logger.info("Opresc Midea AC")

        if self._use_library:
            try:
                device_info = self._discover_device()
                if device_info:
                    dev = self._lib_device_class(
                        device_ip=device_info.ip,
                        device_id=int(device_info.id),
                        device_type=settings.MIDEA_DEVICE_TYPE,
                    )
                    dev.refresh()
                    dev.power_state = False
                    dev.apply()
                    logger.info("Midea AC oprit cu succes")
                    return True
            except Exception as e:
                logger.error(f"Eroare oprire Midea: {e}")

        logger.warning("Nu am putut opri AC-ul Midea (bibliotecă indisponibilă)")
        return False

    def set_temperature(self, temp):
        """Setează temperatura."""
        if self._use_library:
            try:
                device_info = self._discover_device()
                if device_info:
                    dev = self._lib_device_class(
                        device_ip=device_info.ip,
                        device_id=int(device_info.id),
                        device_type=settings.MIDEA_DEVICE_TYPE,
                    )
                    dev.refresh()
                    dev.target_temperature = temp
                    dev.apply()
                    return True
            except Exception as e:
                logger.error(f"Eroare setare temperatură Midea: {e}")
        return False
