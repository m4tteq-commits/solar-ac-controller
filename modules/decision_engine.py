"""Motorul de decizie - determină când să pornească/oprească AC-ul.

Implementează:
  - Histerezis pentru pornire/oprire (evită ciclarea rapidă)
  - Timp minim de funcționare (protejare compresor)
  - Timp minim de cooldown după oprire
  - Niciodată alimentare din baterie - doar surplus solar direct
"""
import logging
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger('decision')


class DecisionEngine:
    """Logica de decizie pentru controlul AC-ului."""

    def __init__(self):
        self._last_on_time = None
        self._last_off_time = None
        self._last_decision = 'none'
        self._last_reason = 'Inițializare'
        self._ac_on = False

    @property
    def ac_on(self):
        return self._ac_on

    def decide(self, surplus_kw, indoor_temp, battery_charging=True):
        """
        Determină acțiunea de luat.

        Args:
            surplus_kw: Surplus de energie solară (kW)
            indoor_temp: Temperatura interioară (°C) sau None
            battery_charging: True dacă bateria se încarcă (solar > consum)

        Returns:
            dict cu 'action' (turn_on/turn_off/none) și 'reason'
        """
        now = datetime.now()
        current_hour = now.hour

        # 1. Verificare ore permise
        if current_hour < settings.ALLOWED_HOURS_START or current_hour >= settings.ALLOWED_HOURS_END:
            if self._ac_on:
                return self._make_decision('turn_off',
                    f'Ora {now.strftime("%H:%M")}: în afara programului ({settings.ALLOWED_HOURS_START}:00-{settings.ALLOWED_HOURS_END}:00)')
            return self._make_decision('none',
                f'Ora {now.strftime("%H:%M")}: în afara programului')

        # 2. Verificare temperatură interioară
        if indoor_temp is not None and indoor_temp < settings.TEMP_THRESHOLD:
            if self._ac_on:
                return self._make_decision('turn_off',
                    f'T° interior {indoor_temp:.1f}°C < prag {settings.TEMP_THRESHOLD}°C')
            return self._make_decision('none',
                f'T° interior {indoor_temp:.1f}°C sub pragul de {settings.TEMP_THRESHOLD}°C')

        # 3. Protecție compresor: timp minim de funcționare
        if self._ac_on and self._last_on_time:
            runtime = (now - self._last_on_time).total_seconds() / 60.0
            if runtime < settings.MIN_RUN_TIME_MINUTES:
                return self._make_decision('none',
                    f'Protejare compresor: funcționează de {runtime:.0f}min, '
                    f'minim {settings.MIN_RUN_TIME_MINUTES}min')

        # Protecție compresor: cooldown după oprire
        if not self._ac_on and self._last_off_time:
            cooldown = (now - self._last_off_time).total_seconds() / 60.0
            if cooldown < settings.MIN_COOLDOWN_MINUTES:
                return self._make_decision('none',
                    f'Cooldown compresor: oprit de {cooldown:.0f}min, '
                    f'minim {settings.MIN_COOLDOWN_MINUTES}min')

        # 4. Regula de surplus - PORNIRE
        if surplus_kw >= settings.SURPLUS_THRESHOLD_KW:
            if indoor_temp is not None and indoor_temp >= settings.TEMP_THRESHOLD:
                if not self._ac_on:
                    return self._make_decision('turn_on',
                        f'Surplus {surplus_kw:.2f} kW >= prag {settings.SURPLUS_THRESHOLD_KW} kW, '
                        f'T° interior {indoor_temp:.1f}°C >= prag {settings.TEMP_THRESHOLD}°C')
                return self._make_decision('none',
                    f'AC deja pornit, surplus OK ({surplus_kw:.2f} kW)')
            elif indoor_temp is None:
                return self._make_decision('none',
                    'Temperatura interioară necunoscută, aștept')
            else:
                return self._make_decision('none',
                    f'T° interior {indoor_temp:.1f}°C < prag {settings.TEMP_THRESHOLD}°C')

        # 5. Regula de surplus - OPRIRE (histerezis)
        off_threshold = settings.SURPLUS_THRESHOLD_KW - settings.SURPLUS_HYSTERESIS_KW
        if surplus_kw < off_threshold:
            if self._ac_on:
                return self._make_decision('turn_off',
                    f'Surplus {surplus_kw:.2f} kW < prag oprire {off_threshold:.2f} kW')
            return self._make_decision('none',
                f'Surplus insuficient ({surplus_kw:.2f} kW)')

        # 6. Safety: surplus negativ - oprește imediat
        if surplus_kw < 0:
            if self._ac_on:
                return self._make_decision('turn_off',
                    f'Surplus negativ ({surplus_kw:.2f} kW) - se consumă din rețea/baterie')
            return self._make_decision('none',
                f'Surplus negativ ({surplus_kw:.2f} kW), AC rămâne oprit')

        # 7. Zona mortă (histerezis) - nu face nimic
        return self._make_decision('none',
            f'Zona mortă - surplus {surplus_kw:.2f} kW în interval histerezis '
            f'[{off_threshold:.2f} - {settings.SURPLUS_THRESHOLD_KW} kW]')

    def _make_decision(self, action, reason):
        """Înregistrează decizia și actualizează contoarele de timp."""
        self._last_decision = action
        self._last_reason = reason

        if action == 'turn_on':
            self._ac_on = True
            self._last_on_time = datetime.now()
            logger.info(f"DECIZIE PORNIRE: {reason}")
        elif action == 'turn_off':
            self._ac_on = False
            self._last_off_time = datetime.now()
            logger.info(f"DECIZIE OPRIRE: {reason}")
        else:
            logger.debug(f"DECIZIE NICIUNA: {reason}")

        return {
            'action': action,
            'reason': reason,
            'time': datetime.now().strftime('%H:%M:%S'),
        }

    def get_status(self):
        """Returnează starea curentă a motorului de decizie."""
        now = datetime.now()
        runtime_str = None
        if self._ac_on and self._last_on_time:
            mins = (now - self._last_on_time).total_seconds() / 60.0
            runtime_str = f"{mins:.0f} min"

        return {
            'ac_on': self._ac_on,
            'last_decision': self._last_decision,
            'last_decision_reason': self._last_reason,
            'runtime': runtime_str,
        }
