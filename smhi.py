import os
import smtplib
import hashlib
import pathlib
import requests
from collections import defaultdict
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

#Config/Env vars
#LAT = 63.593792
#LON = 20.024406
#Malmö
LAT = 55.593792
LON = 13.024406
#Tresholds
REGN_THRESHOLD = 0.0                                        # mm/h threshold for relevant precipitation (snow, mixed, freezing rain)
ALERT_HOURS = 12                                            # forecast window

# Tröskelvärden för frost och underkylt regn
FROST_TEMP_THRESHOLD = 0.0                                  # °C, vid eller under triggar frostvarning
FREEZING_RAIN_TEMP_LOWER = -2.0                             # °C, nedre gräns för temperatur vid underkylt regn
FREEZING_RAIN_TEMP_UPPER = 2.0                              # °C, övre gräns för temperatur vid underkylt regn

#Email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
LAST_ALERT_FILE = pathlib.Path(".last_alert")

#Build SMHI point-forecast URL for the configured lat/lon
url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{LON}/lat/{LAT}/data.json"
res = requests.get(url)                                     #Send GET request to SMHI
res.raise_for_status()                                      #check the HTTP response status.
data = res.json()                                           #Parse response body as JSON
now_utc = datetime.now(timezone.utc)                        #Current UTC time
end_time = now_utc + timedelta(hours=ALERT_HOURS)           #end of the lookahead window

# Datastruktur för att gruppera alerts per datum OCH tid.
alerts_by_date_time = defaultdict(lambda: defaultdict(list))

#Iterate over forecast time series from SMHI
for period in data.get("timeSeries", []):
    time_utc = datetime.fromisoformat(period["validTime"].replace("Z", "+00:00"))
    if not (now_utc < time_utc <= end_time):
        continue
# Convert UTC time to local zone for nicer display    
    time_local = time_utc.astimezone()
    date_str = time_local.strftime("%Y-%m-%d")
    time_str = time_local.strftime("%H:%M")
# Extract parameters from SMHI "parameters" array:
# - "t" is temperature (°C)
# - "pcat" is precipitation category (1=snow, 2=mixed, 3=rain, 4=drizzle, ...)
# - "pmean" is precipitation rate (mm/h)
    t = next(p["values"][0] for p in period["parameters"] if p["name"] == "t")
    pcat = next(p["values"][0] for p in period["parameters"] if p["name"] == "pcat")
    pmean = next(p["values"][0] for p in period["parameters"] if p["name"] == "pmean")
    
    # För debug - Kommentera bort eller ta bort när du är klar!
    # print(time_local.isoformat(), f"t={t}", f"pmean={pmean}", f"pcat={pcat}")

    # Bestäm om en nederbördsvärning ska triggas (baseras på mängd)
    is_any_precip_occurring = pmean > REGN_THRESHOLD
    
    # 1. Frostvarning (om temperaturen är vid eller under noll)
    if t <= FROST_TEMP_THRESHOLD:
        alerts_by_date_time[date_str][time_str].append(f"🧊 Risk för frost ({t:.1f}°C)")
    
    # 2. Nederbördsvärningar (endast snö, blandat, eller underkylt regn)
    if is_any_precip_occurring:
        # 2a. Underkylt regn / Frysande nederbörd (om regn vid temperaturer nära fryspunkten)
        if pcat in (3, 4) and (FREEZING_RAIN_TEMP_LOWER <= t <= FREEZING_RAIN_TEMP_UPPER):
            alerts_by_date_time[date_str][time_str].append(f"🧊 Risk för underkylt regn/frysande nederbörd ({pmean:.1f} mm/h vid {t:.1f}°C)")
        # 2b. Snö
        elif pcat == 1:
            alerts_by_date_time[date_str][time_str].append(f"❄️ Snö {pmean:.1f} mm/h")
            # Logik för snow_total_mm och heavy_snow_start har tagits bort
        # 2c. Blandad snö/regn (räknas också som en typ av snövarning)
        elif pcat == 2:
            alerts_by_date_time[date_str][time_str].append(f"❄️🌧️ Blandad snö/regn {pmean:.1f} mm/h")

# Platta till alerts för hashning
flat_alerts = []
# heavy_snow_msg hantering för hashning har tagits bort
for date_key in sorted(alerts_by_date_time.keys()):
    flat_alerts.append(date_key)
    for time_key in sorted(alerts_by_date_time[date_key].keys()):
        # Kombinera varningsbeskrivningar för samma tidpunkt till en sträng för hashning
        combined_alerts_for_hashing = " och ".join(alerts_by_date_time[date_key][time_key])
        flat_alerts.append(f"  {time_key}: {combined_alerts_for_hashing}")

# ---- Undvik upprepade varningar ---- # Om filen finns och den lagrade hashen matchar nuvarande hash -> inget har ändrats -> skippa
alert_hash = hashlib.sha256("\n".join(flat_alerts).encode()).hexdigest()
if LAST_ALERT_FILE.exists() and LAST_ALERT_FILE.read_text().strip() == alert_hash:
    print("Inga nya varningar — skippar e-post.")
    exit(0)
LAST_ALERT_FILE.write_text(alert_hash)

#Om det finns varningar, förbered och skicka e-post
if alerts_by_date_time: # Kontrollera endast om det finns timvisa varningar
    RECIPIENTS = [email.strip() for email in TO_EMAIL.split(",") if email.strip()]
# Bygg e-postmeddelandets kropp
    msg_body_lines = []

    for date_key in sorted(alerts_by_date_time.keys()):
        msg_body_lines.append(date_key)
        for time_key in sorted(alerts_by_date_time[date_key].keys()):
            # Slå ihop alla meddelanden för denna specifika tidpunkt med " och " emellan
            combined_alerts = " och ".join(alerts_by_date_time[date_key][time_key])
            msg_body_lines.append(f"  {time_key}: {combined_alerts}")
        msg_body_lines.append("")  # tom rad efter varje dag

    #body = "Vädret i Malmö:\n\n" + "\n".join(msg_body_lines)
    body = "Vädret i Malmö:\n\n" + "\n".join(msg_body_lines)
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = "Frostvarning"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(RECIPIENTS)
    # Skicka via SMTP SSL
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print("Varning skickad:\n", body)
else:
    print("Inga varningar under nästa prognosperiod.")
