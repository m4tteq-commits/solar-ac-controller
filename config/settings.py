"""
Configurare Solar AC Controller
Editează valorile de mai jos conform instalării tale.
"""
# pylint: disable=invalid-name

# ============================================================
# SOLARMAN INVERTOR
# ============================================================
# Acces LOCAL Solarman (stick WiFi pe rețeaua ta) - PRIORITAR
# Port 8899 (Modbus TCP)
SOLARMAN_STICK_IP = "192.168.1.100"  # IP-ul stick-ului Solarman WiFi
SOLARMAN_STICK_PORT = 8899
SOLARMAN_INVERTER_SN = "3127529265"  # Serial number stick WiFi

# Acces API Cloud Solarman - FALLBACK
# home.solarmanpv.com -> Cont -> API Management
SOLARMAN_API_KEY = "AICI_PUNE_API_KEY"
SOLARMAN_API_SECRET = "AICI_PUNE_API_SECRET"
SOLARMAN_APP_ID = 100
SOLARMAN_STATION_ID = "AICI_PUNE_STATION_ID"

# ============================================================
# MIDEA AC (control local prin rețea WiFi)
# ============================================================
MIDEA_DEVICE_ID = "AICI_PUNE_DEVICE_ID"   # Device ID (se obține cu midea-discover)
MIDEA_LOCAL_KEY = "AICI_PUNE_LOCAL_KEY"    # Local key (se obține cu midea-discover)
MIDEA_IP = ""                               # IP local Midea (lasă gol pt auto-detect)
MIDEA_DEVICE_TYPE = 0xAC                    # Tip dispozitiv (0xAC = AC)
MIDEA_SN = "SN000000P0000000Q1AC72DDA7B9A40000"

# ============================================================
# LOGICA DE DECIZIE
# ============================================================
SURPLUS_THRESHOLD_KW = 1.4       # Prag surplus pentru pornire AC (kW)
SURPLUS_HYSTERESIS_KW = 0.2      # Histerezis - oprește când surplus < prag - histerezis
SURPLUS_OFF_THRESHOLD_KW = 0.0   # Oprește AC dacă surplus < 0 kW (safety buffer)
TEMP_THRESHOLD = 24.0            # Temp min interioară pornire (°C)
TARGET_TEMP = 24.0               # Temp țintă când AC pornește (°C)
ALLOWED_HOURS_START = 9          # Pornire automată de la ora
ALLOWED_HOURS_END = 18           # Oprire automată după ora
CHECK_INTERVAL_SECONDS = 60      # Interval verificare (secunde)

# Protecție compresor
MIN_RUN_TIME_MINUTES = 10        # Timp minim de funcționare (minute)
MIN_COOLDOWN_MINUTES = 5         # Timp minim de cooldown după oprire (minute)

# ============================================================
# EMAIL (Gmail SMTP)
# ============================================================
EMAIL_ENABLED = True
EMAIL_SENDER = "matteoiftode3@gmail.com"
EMAIL_PASSWORD = "AICI_PUNE_APP_PASSWORD"  # Gmail App Password (NU parola normală!)
EMAIL_RECIPIENT = "matteoiftode3@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ============================================================
# TELEGRAM BOT
# ============================================================
TELEGRAM_BOT_TOKEN = "AICI_PUNE_BOT_TOKEN"   # Token de la @BotFather
TELEGRAM_CHAT_ID = "AICI_PUNE_CHAT_ID"      # Chat ID

# ============================================================
# WEB UI
# ============================================================
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

# ============================================================
# LOGGING
# ============================================================
LOG_FILE = "/home/anne/solar-ac-controller/solar-ac.log"
LOG_LEVEL = "INFO"
