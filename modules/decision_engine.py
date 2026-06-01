"""Motorul de decizie - determină când să pornească/oprească AC-ul."""
import logging
from datetime import datetime

from config import settings

logger = logging.getLogger('decision')


class DecisionEngine:
    """Logica de decizie pentru controlul AC-ului."""

    def decide(self, surplus_kw, status, now):
        """
        Determină acțiunea de luat.

        Args:
            surplus_kw: Surplus de energie solară (kW)
            status: Dict cu starea curentă (ac_on, indoor_temp, manual_override, etc.)
            now: Ora curentă

        Returns:
            Dict cu 'action' (turn_on/turn_off/none) și 'reason'
        """
        ac_on = status.get('ac_on')
        indoor_temp = status.get('indoor_temp')
        manual_override = status.get('manual_override')

        # 1. Override manual - are prioritate absolută
        if manual_override == 'force_off':
            if ac_on:
                return {'action': 'turn_off', 'reason': 'Override manual: forțat oprit'}
            return {'action': 'none', 'reason': 'Override manual: forțat oprit'}

        if manual_override == 'force_on':
            if not ac_on:
                return {'action': 'turn_on', 'reason': 'Override manual: forțat pornit'}
            return {'action': 'none', 'reason': 'Override manual: forțat pornit'}

        # 2. Verificare ore permise
        current_hour = now.hour
        if current_hour < settings.ALLOWED_HOURS_START or current_hour >= settings.ALLOWED_HOURS_END:
            if ac_on:
                return {'action': 'turn_off', 'reason': f'Ora {now.strftime("%H:%M")}: în afara programului'}
            return {'action': 'none', 'reason': f'Ora {now.strftime("%H:%M")}: în afara programului'}

        # 3. Pornire: surplus >= prag și temperatura > prag
        if surplus_kw >= settings.SURPLUS_THRESHOLD_KW:
            if indoor_temp is not None and indoor_temp >= settings.TEMP_THRESHOLD:
                if not ac_on:
                    return {
                        'action': 'turn_on',
                        'reason': f'Surplus {surplus_kw:.2f} kW >= prag {settings.SURPLUS_THRESHOLD_KW} kW, '
                                  f'T° interior {indoor_temp}°C >= prag {settings.TEMP_THRESHOLD}°C'
                    }
                return {'action': 'none', 'reason': f'AC deja pornit, surplus OK ({surplus_kw:.2f} kW)'}
            elif indoor_temp is None:
                return {'action': 'none', 'reason': 'Temperatura interioară necunoscută, aștept'}
            else:
                return {'action': 'none', 'reason': f'T° interior {indoor_temp}°C < prag {settings.TEMP_THRESHOLD}°C'}

        # 4. Oprire: surplus < prag - histerezis
        elif surplus_kw < (settings.SURPLUS_THRESHOLD_KW - settings.SURPLUS_HYSTERESIS_KW):
            if ac_on:
                return {
                    'action': 'turn_off',
                    'reason': f'Surplus {surplus_kw:.2f} kW < prag {settings.SURPLUS_THRESHOLD_KW - settings.SURPLUS_HYSTERESIS_KW} kW'
                }
            return {'action': 'none', 'reason': f'Surplus insuficient ({surplus_kw:.2f} kW)'}

        # 5. Zona mortă (histerezis) - nu face nimic
        else:
            return {
                'action': 'none',
                'reason': f'Zona mortă - surplus {surplus_kw:.2f} kW în interval histerezis'
            }
