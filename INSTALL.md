# Solar AC Controller - Ghid de Instalare

## Ce face
Aplicația monitorizează în timp real producția solară (Solarman) și consumul casei,
și pornește/oprește automat aerul condiționat (Midea) când există surplus de energie solară.

## Cerințe
- Linux Mint (sau orice Linux cu Python 3.10+)
- Conexiune la internet
- Invertor Solarman cu cont API
- Midea AC cu Wi-Fi (controlat prin MSmartHome)

## Pasul 1: Creează mediu virtual Python

```bash
cd /home/anne/solar-ac-controller
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Pasul 2: Configurează aplicația

Editează `config/settings.py` cu datele tale:

### Solarman API
1. Accesează https://home.solarmanpv.com
2. Mergi la: Cont → API Management
3. Creează o cheie API (primești API Key + API Secret)
4. Notează-le în settings.py:
   - `SOLARMAN_API_KEY`
   - `SOLARMAN_API_SECRET`
   - `SOLARMAN_STATION_ID` (se găsește în URL-ul centralei)
5. Opțional: setează IP-ul local al stick-ului Solarman (`SOLARMAN_STICK_IP`)
   pentru a evita consumul API cloud

### Midea AC
1. Instalează midea-discover:
   ```bash
   pip install midea-local
   ```
2. Rulează descoperirea:
   ```bash
   midea-discover
   ```
3. Notează `device_id` și `local_key` din output
4. Completează în settings.py:
   - `MIDEA_DEVICE_ID`
   - `MIDEA_LOCAL_KEY`

### Gmail App Password
1. Accesează https://myaccount.google.com
2. Securitate → Verificare în 2 pași → Parole aplicații
3. Creează o parolă pentru "Altele" (nume: Solar AC Controller)
4. Copiază parola (16 caractere, fără spații)
5. Completează `EMAIL_PASSWORD` în settings.py

### Telegram Bot
1. Deschide Telegram, caută @BotFather
2. Trimite `/newbot`, urmează pașii
3. Primești un token (ex: `123456:ABC-DEF...`)
4. Completează `TELEGRAM_BOT_TOKEN` în settings.py
5. Trimite `/start` la botul tău creat
6. Accesează https://api.telegram.org/bot<TOKEN>/getUpdates
7. Găsește `"chat":{"id":123456789` — acela e `TELEGRAM_CHAT_ID`

## Pasul 3: Testează

```bash
cd /home/anne/solar-ac-controller
source venv/bin/activate
python main.py
```

Ar trebui să vezi loguri în terminal. Verifică:
- Se citesc datele Solarman?
- Se conectează la Midea?
- Accesează http://localhost:8080 în browser

## Pasul 4: Instalează ca serviciu (auto-start)

```bash
sudo cp solar-ac.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now solar-ac.service
```

Verifică starea:
```bash
sudo systemctl status solar-ac.service
sudo journalctl -u solar-ac.service -f
```

## Pasul 5: Accesează Web UI

Din browser (pe orice dispozitiv din rețeaua ta):
```
http://<IP_LAPTOP>:8080
```

Pentru acces din afara casei, configurează port forwarding pe router
(port 8080 → IP-ul laptopului) sau folosește un serviciu gratuit de tunneling.

## Comenzi Telegram

- `/start` - Bun venit
- `/status` - Stare curentă
- `/on` - Pornire manuală AC
- `/off` - Oprire manuală AC
- `/auto` - Revine la automat
- `/set surplus 1.5` - Schimbă prag surplus
- `/set temp 25` - Schimbă prag temperatură
- `/set ore 9 21` - Schimbă interval orar
- `/raport` - Trimite raport pe email
- `/help` - Ajutor

## Depanare

### Nu se citesc datele Solarman
- Verifică API Key/Secret
- Verifică dacă ai depășit limita de 200K request-uri
- Setează IP-ul local al stick-ului pentru acces local

### Nu se conectează la Midea
- Rulează `midea-discover` pentru a verifica dacă dispozitivul e vizibil
- Asigură-te că laptopul și Midea sunt pe aceeași rețea

### Email nu se trimite
- Verifică Gmail App Password (nu parola normală!)
- Verifică dacă "Acces mai puțin sigur" e dezactivat în Gmail

### Web UI nu pornește
- Verifică dacă portul 8080 e liber: `ss -tlnp | grep 8080`
- Verifică firewall: `sudo ufw allow 8080`
