import os
import requests
from datetime import datetime, timedelta, timezone
import smtplib
from email.message import EmailMessage
import hashlib
import pathlib
from collections import defaultdict
# ----- CONFIG -----
LAT = 55.593792
LON = 13.024406
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
heavy_snow_msg = None
for period in data.get("timeSeries", []):
    time_utc = datetime.fromisoformat(period["validTime"].replace("Z", "+00:00"))
    if not (now_utc < time_utc <= end_time):
        continue
    time_local = time_utc.astimezone()
    date_str = time_local.strftime("%Y-%m-%d")
    time_str = time_local.strftime("%H:%M")
    t = next(p["values"][0] for p in period["parameters"] if p["name"] == "t")
    pcat = next(p["values"][0] for p in period["parameters"] if p["name"] == "pcat")
    pmean = next(p["values"][0] for p in period["parameters"] if p["name"] == "pmean")
    if t < TEMP_THRESHOLD:
        alerts_by_date[date_str].append(f"{time_str}:🥶 Temperatur {t:.1f}°C")
    if pmean > REGN_THRESHOLD:
        if pcat == 1:
            alerts_by_date[date_str].append(f"{time_str}:❄️ Snö {pmean:.1f} mm/h")
            snow_total_mm += pmean
        elif pcat == 2:
            alerts_by_date[date_str].append(f"{time_str}:❄️🌧️ Blandad snö/regn {pmean:.1f} mm/h")
            snow_total_mm += pmean / 2
        elif pcat in (3, 4):
            alerts_by_date[date_str].append(f"{time_str}:🌧️ Regn {pmean:.1f} mm/h")
if snow_total_mm >= SNOW_THRESHOLD:
    heavy_snow_msg = f"❄️❄️❄️Kraftigt snöfall väntas: {snow_total_mm:.1f} mm under {ALERT_HOURS}h"
flat_alerts = []
if heavy_snow_msg:
    flat_alerts.append(heavy_snow_msg)
for date_key in sorted(alerts_by_date.keys()):
    flat_alerts.append(date_key)
    flat_alerts.extend(alerts_by_date[date_key])
# ---- Avoid repeat alerts ----Av kommentera uppåt och i .yml filen
#alert_hash = hashlib.sha256("\n".join(all_alerts_list).encode()).hexdigest()
#if LAST_ALERT_FILE.exists() and LAST_ALERT_FILE.read_text().strip() == alert_hash:
#    print("Inga nya varningar — skippar e-post.")
#    exit(0)
#LAST_ALERT_FILE.write_text(alert_hash)
if alerts_by_date or heavy_snow_msg:
    RECIPIENTS = [email.strip() for email in TO_EMAIL.split(",") if email.strip()]
    msg_body_lines = []
    if heavy_snow_msg:
        msg_body_lines.append("SNÖVARNING!")
        msg_body_lines.append(heavy_snow_msg)
        msg_body_lines.append("")  # blank line after headline
    for date_key in sorted(alerts_by_date.keys()):
        msg_body_lines.append(date_key)
        for alert_msg in alerts_by_date[date_key]:
            msg_body_lines.append(f"  {alert_msg}")
        msg_body_lines.append("")  # blank line after each day
    body = "Vädervarningar för snöröjargänget:\n\n" + "\n".join(msg_body_lines)
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
