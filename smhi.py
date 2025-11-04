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
now = datetime.now(timezone.utc)
end_time = now + timedelta(hours=ALERT_HOURS)
alerts = []
snow_total_mm = 0.0

for period in data.get("timeSeries", []):
    # Parse forecast time
    time_utc = datetime.fromisoformat(period["validTime"].replace("Z", "+00:00"))
    if not (now_utc <= time_utc <= end_time):
        continue
    # Convert to local time for readability
    time_local = time_utc.astimezone()
    time_str = time_local.strftime("%Y-%m-%d %H:%M")  # Clean timestamp
    # Extract parameters
    t = next(p["values"][0] for p in period["parameters"] if p["name"] == "t")
    pcat = next(p["values"][0] for p in period["parameters"] if p["name"] == "pcat")
    pmean = next(p["values"][0] for p in period["parameters"] if p["name"] == "pmean")
    # Temperature alert
    if t < TEMP_THRESHOLD:
        alerts.append(f"{time_str}:🥶 Temperatur {t:.1f}°C")
    # Precipitation alerts
    if pmean > REGN_THRESHOLD:
        if pcat == 1:
            alerts.append(f"{time_str}:❄️ Snö {pmean:.1f} mm/h")
            snow_total_mm += pmean
        elif pcat == 2:
            alerts.append(f"{time_str}:❄️🌧️ Blandad snö/regn {pmean:.1f} mm/h")
            snow_total_mm += pmean / 2
        elif pcat in (3, 4):
            alerts.append(f"{time_str}:🌧️ Regn {pmean:.1f} mm/h")
# Heavy snow threshold check
if snow_total_mm >= SNOW_THRESHOLD:
    alerts.append(f"Kraftigt snöfall väntas: {snow_total_mm:.1f} mm under {ALERT_HOURS}h")

# ---- Avoid repeat alerts ----
#alerts_sorted = sorted(alerts)
#alert_hash = hashlib.sha256("\n".join(alerts_sorted).encode()).hexdigest()
#if LAST_ALERT_FILE.exists():
#    if LAST_ALERT_FILE.read_text().strip() == alert_hash:
#        print("No new alerts — skipping email.")
#        exit(0)
#LAST_ALERT_FILE.write_text(alert_hash)

# ---- Send email if alerts exist ----
if alerts:
    RECIPIENTS = [email.strip() for email in TO_EMAIL.split(",") if email.strip()]
    msg = EmailMessage()
    body = "Väder rapporter snöröjargänget:\n\n" + "\n".join(alerts)
    msg.set_content(body)
    msg["Subject"] = "Vädervarning"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(RECIPIENTS)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg, from_addr=EMAIL_ADDRESS, to_addrs=RECIPIENTS)
    print("Varning skickad:\n", alerts)
else:
    print("No alerts in next forecast window.")
