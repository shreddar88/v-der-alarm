import os
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("OPENWEATHER_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

LAT, LON = 55.593792, 13.024406

# Malmö timezone offset
CET_OFFSET = timedelta(hours=2)  # UTC+2 (adjust manually for winter UTC+1)

url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&units=metric&appid={API_KEY}"
response = requests.get(url)
data = response.json()

if "list" not in data:
    print("Error fetching forecast:", data)
    raise SystemExit("Missing forecast data (check API key or endpoint)")

now_utc = datetime.utcnow()
rain_forecasts = []

# Check next 3 hours for rain or temperature < 0
for forecast in data["list"]:
    forecast_time_utc = datetime.utcfromtimestamp(forecast["dt"])
    if forecast_time_utc > now_utc + timedelta(hours=3):
        break

    temp = forecast["main"]["temp"]
    rain = forecast.get("rain", {}).get("3h", 0)
    if temp < 0 or rain > 0:
        # Convert to Malmö local time
        forecast_time_local = forecast_time_utc + CET_OFFSET
        rain_forecasts.append((forecast_time_local, temp, rain))

if rain_forecasts:
    start_time = rain_forecasts[0][0].strftime('%H:%M')
    end_time = rain_forecasts[-1][0].strftime('%H:%M')
    messages = []
    for f_time, temp, rain in rain_forecasts:
        rain_msg = f", Rain: {rain} mm" if rain > 0 else ""
        messages.append(f"{f_time.strftime('%H:%M')} - Temp: {temp}°C{rain_msg}")
    
    alert_msg = f"⚠️ Weather Alert for Malmö (next 3 hours)\nTime range: {start_time}–{end_time}\nDetails:\n" + "\n".join(messages)

    msg = EmailMessage()
    msg.set_content(alert_msg)
    msg["Subject"] = "Weather Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print("Alert sent:\n", alert_msg)
else:
    print("No rain or freezing temperature expected in the next 3 hours.")
