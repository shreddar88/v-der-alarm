import os
import requests
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.text import MIMEText
import hashlib
import pathlib

# ----- CONFIG -----
LAT = 55.593792
LON = 13.024406
TEMP_THRESHOLD = 0.0          # °C, below triggers alert
PRECIP_THRESHOLD = 0.0        # mm/h threshold for rain/snow alerts
HEAVY_SNOW_THRESHOLD = 20.0   # mm in ALERT_HOURS total
ALERT_HOURS = 24               # forecast window
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_USER = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
RECIPIENTS = os.environ["TO_EMAIL"].split(",")
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
    time = datetime.fromisoformat(period["validTime"].replace("Z", "+00:00"))
    if not (now <= time <= end_time):
        continue

    # Extract parameters
    t = next(p["values"][0] for p in period["parameters"] if p["name"] == "t")
    pcat = next(p["values"][0] for p in period["parameters"] if p["name"] == "pcat")
    pmean = next(p["values"][0] for p in period["parameters"] if p["name"] == "pmean")
    if t < TEMP_THRESHOLD:
        alerts.append(f"{time}: Temp {t}°C")
    if pmean > PRECIP_THRESHOLD:
        if pcat == 1:
            alerts.append(f"{time}: Snow {pmean} mm/h")
            snow_total_mm += pmean
        elif pcat == 2:
            alerts.append(f"{time}: Mixed snow/rain {pmean} mm/h")
            snow_total_mm += pmean / 2
        elif pcat in (3, 4):
            alerts.append(f"{time}: Rain {pmean} mm/h")

if snow_total_mm >= HEAVY_SNOW_THRESHOLD:
    alerts.append(f"Heavy snow expected: {snow_total_mm:.1f} mm in next {ALERT_HOURS}h")

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
    body = "Weather alerts for your location:\n\n" + "\n".join(alerts)
    msg = MIMEText(body)
    msg["Subject"] = "Snow/Rain Alert 🚨"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(RECIPIENTS)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, RECIPIENTS, msg.as_string())
    print("Email sent with alerts.")
else:
    print("No alerts in next forecast window.")
