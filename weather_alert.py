import os
import json
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

API_KEY = os.getenv("OPENWEATHER_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")  # comma-separated emails

LAT, LON = 55.593792, 13.024406  # Spånehusvägen 87, Malmö
CET_OFFSET = timedelta(hours=2)   # UTC+2 (CEST)
TEMP_THRESHOLD = 20               # Celsius
RAIN_THRESHOLD = 0                # mm

# ALERT_LOG_FILE = "alert_log.json" # store past alert times
# today_str = datetime.utcnow().date().isoformat()
# if os.path.exists(ALERT_LOG_FILE):
# with open(ALERT_LOG_FILE, "r") as f:
# alert_log = json.load(f)
# else:
# alert_log = {}
# alerts_today = alert_log.get(today_str, [])
# if len(alerts_today) >= 2:
# print("Max två varningar redan skickade idag, hoppar över.")
# exit()

url = f"[https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&units=metric&appid={API_KEY}](https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&units=metric&appid={API_KEY})"
response = requests.get(url)
data = response.json()
now_utc = datetime.utcnow()
alert_forecasts = []

# CHECK NEXT 3 HOURS

for forecast in data["list"]:
forecast_time_utc = datetime.utcfromtimestamp(forecast["dt"])
if forecast_time_utc > now_utc + timedelta(hours=3):
break

```
temp = forecast["main"]["temp"]
rain = forecast.get("rain", {}).get("3h", 0)

if temp < TEMP_THRESHOLD or rain > RAIN_THRESHOLD:
    forecast_time_local = forecast_time_utc + CET_OFFSET
    alert_forecasts.append((forecast_time_local, temp, rain))
```

# SEND ALERT IF ANY

if alert_forecasts:
recipients = [email.strip() for email in TO_EMAIL.split(",") if email.strip()]

```
# Determine time range
if len(alert_forecasts) > 1:
    start_time = alert_forecasts[0][0].strftime('%H:%M')
    end_time = alert_forecasts[-1][0].strftime('%H:%M')
    time_range = f"mellan {start_time}–{end_time}"
else:
    forecast_time = alert_forecasts[0][0].strftime('%H:%M')
    time_range = f"kring {forecast_time}"

# Determine weather type
if any(rain > RAIN_THRESHOLD for _, _, rain in alert_forecasts):
    header = f"🌧️ Regn förväntas {time_range}\nDetaljer:"
elif any(temp < TEMP_THRESHOLD for _, temp, _ in alert_forecasts):
    header = f"🥶 Kallt väder förväntas {time_range}\nDetaljer:"
else:
    header = f"⚠️ Vädret i Malmö {time_range}\nDetaljer:"

# Build messages
messages = []
for f_time, temp, rain in alert_forecasts:
    time_label = "Nu" if abs((f_time - (now_utc + CET_OFFSET)).total_seconds()) < 3600 else f_time.strftime('%H:%M')
    rain_msg = f", Regn: {rain} mm" if rain > 0 else ""
    messages.append(f"{time_label} - Temp: {temp:.1f}°C{rain_msg}")
alert_msg = header + "\n" + "\n".join(messages)

# Send email
msg = EmailMessage()
msg.set_content(alert_msg)
msg["Subject"] = "Vädervarning"
msg["From"] = EMAIL_ADDRESS
msg["To"] = ", ".join(recipients)  # display only
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    smtp.send_message(msg, from_addr=EMAIL_ADDRESS, to_addrs=recipients)

# Update alert log
# alerts_today.append(datetime.utcnow().isoformat())
# alert_log[today_str] = alerts_today
# with open(ALERT_LOG_FILE, "w") as f:
#     json.dump(alert_log, f)

print("Varning skickad:\n", alert_msg)
```
else:
print("Ingen regn- eller temperaturvarning för de kommande 3 timmarna.")
