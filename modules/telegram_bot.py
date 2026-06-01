"""Bot Telegram - comandări și notificări."""
import logging
import threading
import time

from config import settings

logger = logging.getLogger('telegram')

try:
    from telegram import Update, Bot
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    logger.warning("python-telegram-bot neinstalat. Telegram dezactivat.")
    TELEGRAM_AVAILABLE = False


class TelegramBot:
    """Bot Telegram pentru control și monitorizare."""

    def __init__(self, controller):
        self.controller = controller
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.app = None
        self._pending_messages = []
        self._running = True

    def run(self):
        """Pornește botul Telegram."""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot nu e instalat. Rulează: pip install python-telegram-bot")
            return

        try:
            self.app = Application.builder().token(self.token).build()

            # Comenzi
            self.app.add_handler(CommandHandler("start", self._cmd_start))
            self.app.add_handler(CommandHandler("status", self._cmd_status))
            self.app.add_handler(CommandHandler("on", self._cmd_on))
            self.app.add_handler(CommandHandler("off", self._cmd_off))
            self.app.add_handler(CommandHandler("auto", self._cmd_auto))
            self.app.add_handler(CommandHandler("set", self._cmd_set))
            self.app.add_handler(CommandHandler("raport", self._cmd_report))
            self.app.add_handler(CommandHandler("help", self._cmd_help))

            logger.info("Bot Telegram pornit")
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Eroare bot Telegram: {e}")

    def stop(self):
        self._running = False
        if self.app:
            self.app.stop()

    def send_status_msg(self, text):
        """Trimite mesaj de stare către chat."""
        if not self.app or not TELEGRAM_AVAILABLE:
            return
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            bot = Bot(token=self.token)
            loop.run_until_complete(
                bot.send_message(chat_id=self.chat_id, text=text)
            )
            loop.close()
            logger.info(f"Mesaj Telegram trimis: {text[:60]}...")
        except Exception as e:
            logger.error(f"Eroare trimitere mesaj Telegram: {e}")

    # ---- Command handlers ----

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start - Bun venit."""
        welcome = (
            "☀️ Solar AC Controller ☀️\n\n"
            "Bun venit! Acest bot controlează aerul condiționat\n"
            "în funcție de surplusul de energie solară.\n\n"
            "Comenzi disponibile:\n"
            "/status - Starea curentă\n"
            "/on - Pornește AC manual\n"
            "/off - Oprește AC manual\n"
            "/auto - Mod automat\n"
            "/set - Setează parametri\n"
            "/raport - Raport zilnic\n"
            "/help - Ajutor"
        )
        await update.message.reply_text(welcome)

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status - Starea sistemului."""
        s = self.controller.last_status
        if s.get('ac_on') is None:
            text = "⚠️ Nu am date încă. Prima verificare va veni într-un minut."
        else:
            text = (
                f"☀️ Producție solară: {s.get('solar_production_kw', '?')} kW\n"
                f"🏠 Consum casă: {s.get('consumption_kw', '?')} kW\n"
                f"📊 Surplus: {s.get('surplus_kw', '?')} kW\n"
                f"🔋 Baterie: {s.get('battery_soc', '?')}%\n"
                f"─────────────────\n"
                f"❄️ AC: {'🟢 PORNIT' if s.get('ac_on') else '🔴 OPRIT'}\n"
                f"🌡️ T° interior: {s.get('indoor_temp', '?')}°C\n"
                f"🌤️ T° exterior: {s.get('outdoor_temp', '?')}°C\n"
                f"─────────────────\n"
                f"📋 Ultima decizie: {s.get('last_decision', '?')}\n"
                f"   {s.get('last_decision_reason', '')}\n"
                f"\n🕐 Actualizat: {s.get('last_decision_time', '?')}"
            )

            # Manual override indicator
            override = s.get('manual_override')
            if override:
                text += f"\n\n⚙️ Mod manual activ: {override}"
            else:
                text += "\n\n✅ Mod automat"

        await update.message.reply_text(text)

    async def _cmd_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/on - Pornește AC manual."""
        self.controller.last_status['manual_override'] = 'force_on'
        await update.message.reply_text(
            "⚙️ AC setat MANUAL PORNIT.\n"
            "Automatizarea e suspendată până la /auto sau /off."
        )

    async def _cmd_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/off - Oprește AC manual."""
        self.controller.last_status['manual_override'] = 'force_off'
        await update.message.reply_text(
            "⚙️ AC setat MANUAL OPRIT.\n"
            "Automatizarea e suspendată până la /auto."
        )

    async def _cmd_auto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/auto - Revine la mod automat."""
        self.controller.last_status['manual_override'] = None
        await update.message.reply_text(
            "✅ Mod AUTOMAT activat.\n"
            "AC-ul va porni/opri automat în funcție de surplusul solar."
        )

    async def _cmd_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/set - Setează parametri."""
        args = context.args
        if len(args) < 2:
            s = self.controller.last_status
            text = (
                "⚙️ Setări curente:\n"
                f"- Prag surplus: {s.get('surplus_threshold', '?')} kW\n"
                f"- Prag temp: {s.get('temp_threshold', '?')}°C\n"
                f"- Ore: {s.get('hours_start', '?')}:00-{s.get('hours_end', '?')}:00\n\n"
                "Schimbă cu:\n"
                "/set surplus 1.5 - prag surplus (kW)\n"
                "/set temp 25 - prag temperatură (°C)\n"
                "/set ore 9 21 - ore funcționare\n"
            )
        else:
            try:
                if args[0] == 'surplus':
                    val = float(args[1])
                    settings.SURPLUS_THRESHOLD_KW = val
                    self.controller.last_status['surplus_threshold'] = val
                    text = f"✅ Prag surplus setat la {val} kW"
                elif args[0] == 'temp':
                    val = float(args[1])
                    settings.TEMP_THRESHOLD = val
                    self.controller.last_status['temp_threshold'] = val
                    text = f"✅ Prag temperatură setat la {val}°C"
                elif args[0] == 'ore':
                    start = int(args[1])
                    end = int(args[2]) if len(args) > 2 else 22
                    settings.ALLOWED_HOURS_START = start
                    settings.ALLOWED_HOURS_END = end
                    self.controller.last_status['hours_start'] = start
                    self.controller.last_status['hours_end'] = end
                    text = f"✅ Program setat: {start}:00 - {end}:00"
                else:
                    text = "⚠️ Parametru necunoscut. Vezi /set gol."
            except (ValueError, IndexError):
                text = "⚠️ Valoare invalidă. Exemplu: /set surplus 1.5"

        await update.message.reply_text(text)

    async def _cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/raport - Trimite raport zilnic."""
        self.controller.emailer.send_daily_report(self.controller.last_status)
        await update.message.reply_text("📧 Raport trimis pe email.")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help - Ajutor."""
        text = (
            "☀️ Solar AC Controller - Ajutor\n\n"
            "🚀 Comenzi rapide:\n"
            "/status - Stare curentă completă\n"
            "/on - Pornire AC manual\n"
            "/off - Oprire AC manual\n"
            "/auto - Mod automat\n\n"
            "⚙️ Setări:Setări:\n"
            "/set surplus 1.5 - prag surplus (kW)\n"
            "/set temp 25 - prag temperatura (°C)\n"
            "/set ore 9 21 - interval orar\n\n"
            "📧 Altele:\n"
            "/raport - Raport pe email\n"
            "/help - Acest mesaj\n\n"
            "💡 Logica automată:\n"
            "AC pornește când surplus solar >= prag\n"
            "Și temperatura interioară >= prag temp\n"
            "AC oprește când surplus scade sub prag\n"
            "Funcționează doar în orele setate"
        )
        await update.message.reply_text(text)
