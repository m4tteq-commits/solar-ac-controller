"""
Configurare Solar AC Controller
Editează valorile de mai jos conform instalării tale.
"""
# pylint: disable=invalid-name

# ============================================================
# SOLARMAN API
# ============================================================
# Acces API Cloud Solarman - home.solarmanpv.com -> Cont -> API Management
SOLARMAN_API_KEY="AICI_PUNE_API_KEY"          # API Key din contul Solarman
SOLARMAN_API_SECRET="AICI_PUNE_API_SECRET"    # API Secret din contul Solarman
SOLARMAN_APP_ID = 100                         # App ID (de obicei 100)

# ID-ul centralei/invertorului din Solarman
SOLARMAN_STATION_ID = "AICI_PUNE_STATION_ID"  # URL-ul dashboard-ului Solarman
SOLARMAN_INVERTER_SN = "2411121335"           # Serial number invertor

# Acces LOCAL Solarman (stick WiFi pe rețeaua ta)
SOLARMAN_STICK_IP = ""  # ex: "192.168.1.100" - verifică în router

# ============================================================
# MIDEA AC (control local prin rețea WiFi)
# ============================================================
MIDEA_DEVICE_ID = "AICI_PUNE_DEVICE_ID"   # Device ID (se obține cu midea-discover)
MIDEA_LOCAL_KEY = "AICI_PUNE_LOCAL_KEY"    # Local key (se obține cu midea-discover)
MIDEA_IP = ""                               # IP local Midea (lasă gol pt auto-detect)
MIDEA_DEVICE_TYPE = 0xAC                    # Tip dispozitiv (0xAC = AC)

# ============================================================
# LOGICA DE DECIZIE
# ============================================================
SURPLUS_THRESHOLD_KW = 1.4    # Prag surplus pentru pornire AC (kW)
SURPLUS_HYSTERESIS_KW = 0.2   # Histerezis - oprește când surplus < prag - histerezis
TEMP_THRESHOLD = 24.0         # Temp min interioară pornire (grC)
TARGET_TEMP = 24.0            # Temp țintă când AC pornește (grC)
ALLOWED_HOURS_START = 8       # Pornire automată de la ora
ALLOWED_HOURS_END = 22        # Oprire automată după ora
CHECK_INTERVAL_SECONDS = 60   # Interval verificare (secunde)

# ============================================================
# EMAIL (Gmail SMTP)
# ============================================================
EMAIL_ENABLED = True
EMAIL_SENDER = "matteoiftode3@gmail.com"
EMAIL_PASSWORD="AICI_PUNE_APP_PASSWORD"    # Gmail App Password (NU parola normală!)
EMAIL_RECIPIENT = "matteoiftode3@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ============================================================
# TELEGRAM BOT
# ============================================================
TELEGRAM_BOT_TOKEN="AICI_PUNE_BOT_TOKEN"   # Token de la @BotFather
TELEGRAM_CHAT_ID = "AICI_PUNE_CHAT_ID"    # Chat ID (te îl dă botul când /start)

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
