import os
import requests
from datetime import datetime, timedelta, timezone
import smtplib
from email.message import EmailMessage
import hashlib
import pathlib

# ----- CONFIG -----
#MalmöSpånehus
#LAT = 55.593792
#LON = 13.024406
#JönköpingNedan
LAT = 57.450
LON = 14.100
TEMP_THRESHOLD = 20.0          # °C, below triggers alert
REGN_THRESHOLD = 0.0        # mm/h threshold for rain/snow alerts
SNOW_THRESHOLD = 20.0   # mm in ALERT_HOURS total
ALERT_HOURS = 12               # forecast window
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
#LAST_ALERT_FILE = pathlib.Path(".last_alert")
# -------------------

url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{LON}/lat/{LAT}/data.json"
res = requests.get(url)
res.raise_for_status()
data = res.json()
now_utc = datetime.now(timezone.utc)
end_time = now_utc + timedelta(hours=ALERT_HOURS)
alerts_by_date = defaultdict(list)
snow_total_mm = 0.0

# Loop through forecast periods
for period in data.get("timeSeries", []):
    time_utc = datetime.fromisoformat(period["validTime"].replace("Z", "+00:00"))

    # Only future timestamps
    if not (now_utc < time_utc <= end_time):
        continue

    # Local time for display
    time_local = time_utc.astimezone()
    date_str = time_local.strftime("%Y-%m-%d")
    time_str = time_local.strftime("%H:%M")

    # Extract parameters
    t = next(p["values"][0] for p in period["parameters"] if p["name"] == "t")
    pcat = next(p["values"][0] for p in period["parameters"] if p["name"] == "pcat")
    pmean = next(p["values"][0] for p in period["parameters"] if p["name"] == "pmean")

    # Temperature alert
    if t < TEMP_THRESHOLD:
        alerts_by_date[date_str].append(f"{time_str}:🥶 Temperatur {t:.1f}°C")

    # Precipitation alerts
    if pmean > REGN_THRESHOLD:
        if pcat == 1:
            alerts_by_date[date_str].append(f"{time_str}:❄️ Snö {pmean:.1f} mm/h")
            snow_total_mm += pmean
        elif pcat == 2:
            alerts_by_date[date_str].append(f"{time_str}:❄️🌧️ Blandad snö/regn {pmean:.1f} mm/h")
            snow_total_mm += pmean / 2
        elif pcat in (3, 4):
            alerts_by_date[date_str].append(f"{time_str}:🌧️ Regn {pmean:.1f} mm/h")

# Heavy snow check
if snow_total_mm >= SNOW_THRESHOLD:
    alerts_by_date["SNÖVARNING"].append(
        f"❄️❄️❄️Kraftigt snöfall väntas: {snow_total_mm:.1f} mm under {ALERT_HOURS}h"
    )

# Flatten to sorted list for hashing
all_alerts_list = []
for date_key in sorted(alerts_by_date.keys()):
    all_alerts_list.append(date_key)
    all_alerts_list.extend(alerts_by_date[date_key])

# ---- Avoid repeat alerts ----
alert_hash = hashlib.sha256("\n".join(all_alerts_list).encode()).hexdigest()
if LAST_ALERT_FILE.exists() and LAST_ALERT_FILE.read_text().strip() == alert_hash:
    print("Inga nya varningar — skippar e-post.")
    exit(0)
LAST_ALERT_FILE.write_text(alert_hash)

# ---- Send email ----
if alerts_by_date:
    RECIPIENTS = [email.strip() for email in TO_EMAIL.split(",") if email.strip()]
    msg_body_lines = []
    for date_key in sorted(alerts_by_date.keys()):
        msg_body_lines.append(date_key)
        for alert_msg in alerts_by_date[date_key]:
            msg_body_lines.append(f"  {alert_msg}")
        msg_body_lines.append("")  # blank line after each day

    body = "Vädervarningar för din plats:\n\n" + "\n".join(msg_body_lines)
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = "Vädervarning"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(RECIPIENTS)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print("Varning skickad:\n", body)
else:
    print("Inga varningar under nästa prognosperiod.")
