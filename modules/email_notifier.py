"""Notificări prin Email (Gmail SMTP)."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from config import settings

logger = logging.getLogger('email')


class EmailNotifier:
    """Trimite notificări prin email (Gmail SMTP)."""

    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED
        self.sender = settings.EMAIL_SENDER
        self.password = settings.EMAIL_PASSWORD
        self.recipient = settings.EMAIL_RECIPIENT
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self._last_subject = None
        self._last_sent_time = 0
        self._min_interval = 300  # Minim 5 minute între emailuri (anti-spam)

    def send_notification(self, subject, body):
        """Trimite un email de notificare."""
        if not self.enabled:
            logger.debug("Notificările email sunt dezactivate")
            if subject != "test":
                return True
            # Permite test chiar dacă e dezactivat
            pass

        # Anti-spam: nu trimite același subiect prea des
        import time
        now = time.time()
        if subject == self._last_subject and (now - self._last_sent_time) < self._min_interval:
            logger.debug(f"Email '{subject}' ignorat (anti-spam, {int(now - self._last_sent_time)}s)")
            return True

        try:
            msg = MIMEMultipart()
            msg['From'] = f"Solar AC Controller <{self.sender}>"
            msg['To'] = self.recipient
            msg['Subject'] = f"[Solar AC] {subject}"

            # Adaugă header cu data
            full_body = f"Data: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n{body}"
            full_body += "\n\n---\nSolar AC Controller - Automatizare energie solară"

            msg.attach(MIMEText(full_body, 'plain', 'utf-8'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.recipient, msg.as_string())
            server.quit()

            self._last_subject = subject
            self._last_sent_time = now
            logger.info(f"Email trimis: {subject}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("Eroare autentificare Gmail - verifică App Password")
            return False
        except Exception as e:
            logger.error(f"Eroare trimitere email: {e}")
            return False

    def send_daily_report(self, status):
        """Trimite raport zilnic."""
        body = f"""
Raport zilnic Solar AC Controller
==================================

Stare curentă:
- AC: {'PORNIT' if status.get('ac_on') else 'OPRIT'}
- Producție solară: {status.get('solar_production_kw', '?')} kW
- Consum casă: {status.get('consumption_kw', '?')} kW
- Surplus: {status.get('surplus_kw', '?')} kW
- Temperatură interioară: {status.get('indoor_temp', '?')}°C
- Temperatură exterioară: {status.get('outdoor_temp', '?')}°C
- Baterie: {status.get('battery_soc', '?')}%
- Ultima decizie: {status.get('last_decision', '?')}
- Ultima actualizare: {status.get('last_decision_time', '?')}

Setări active:
- Prag surplus: {status.get('surplus_threshold', '?')} kW
- Prag temperatură: {status.get('temp_threshold', '?')}°C
- Program: {status.get('hours_start', '?')}:00 - {status.get('hours_end', '?')}:00
"""
        return self.send_notification("📊 Raport zilnic", body)
