"""Client Midea AC - control local prin rețea WiFi."""
import logging
import socket
import struct
import json

from config import settings

logger = logging.getLogger('midea')


class MideaClient:
    """Comunicare locală cu AC-ul Midea prin protocolul midea-lan."""

    MIDEA_PORT = 6444

    # Comenzi Midea (protocol simplificat)
    CMD_GET_STATUS = 0x01
    CMD_SET_POWER = 0x02
    CMD_SET_TEMP = 0x03
    CMD_SET_MODE = 0x04
    CMD_SET_FAN = 0x05

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

        # Încearcă să folosești biblioteca midea-local (mai robustă)
        try:
            from midea.device import AirConditioningDevice
            from midea.discover import discover
            self._use_library = True
            self._lib_discover = discover
            self._lib_device_class = AirConditioningDevice
            logger.info("Biblioteca midea-local disponibilă")
        except ImportError:
            logger.warning(
                "Biblioteca midea-local nu e instalată. "
                "Instalează cu: pip install midea-local"
            )

    def _discover_device(self):
        """Descoperă dispozitivul Midea pe rețea."""
        if not self._use_library:
            return None

        try:
            devices = self._lib_discover()
            for dev in devices:
                if str(dev.id) == self.device_id or self.device_ip == dev.ip:
                    return dev
            return None
        except Exception as e:
            logger.error(f"Eroare descoperire Midea: {e}")
            return None

    def _send_command_lib(self, device, command_type, value):
        """Trimite comandă folosind biblioteca midea-local."""
        try:
            device = self._lib_device_class(
                device_ip=device.ip,
                device_id=int(device.id),
                device_type=settings.MIDEA_DEVICE_TYPE,
            )
            device.refresh()

            if command_type == 'power':
                device.power_state = value
            elif command_type == 'mode':
                device.mode = self.MODES.get(value, 0x01)
            elif command_type == 'temp':
                device.target_temperature = value
            elif command_type == 'fan':
                device.fan_speed = value

            device.apply()
            return True
        except Exception as e:
            logger.error(f"Eroare comandă Midea: {e}")
            return False

    def get_state(self):
        """Citește starea actuală a AC-ului."""
        # Varianta cu biblioteca midea-local
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
                }
            except Exception as e:
                logger.error(f"Eroare citire stare Midea: {e}")
                return None

        # Fallback - protocol direct (simplificat)
        try:
            return {
                'is_on': None,  # Nu se poate citi fără bibliotecă
                'indoor_temp': None,
                'outdoor_temp': None,
                'target_temp': None,
                'mode': None,
                'fan_speed': None,
            }
        except Exception:
            return None

    def turn_on(self, temp=24.0, mode='cool', fan_speed='auto'):
        """Pornește AC-ul."""
        logger.info(f"Pornesc Midea AC: {temp}°C, mod {mode}, fan {fan_speed}")

        if self._use_library:
            try:
                device_info = self._discover_device()
                if device_info:
                    self._send_command_lib(device_info, 'power', True)
                    self._send_command_lib(device_info, 'mode', mode)
                    self._send_command_lib(device_info, 'temp', temp)
                    self._send_command_lib(device_info, 'fan', fan_speed)
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
                    self._send_command_lib(device_info, 'power', False)
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
                    self._send_command_lib(device_info, 'temp', temp)
                    return True
            except Exception as e:
                logger.error(f"Eroare setare temperatură Midea: {e}")
        return False
