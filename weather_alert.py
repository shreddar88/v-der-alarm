import os
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# Environment variables
API_KEY = os.getenv("OPENWEATHER_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")  # comma-separated emails

# Malmö coordinates
LAT, LON = 55.593792, 13.024406

# Malmö timezone offset (CET/CEST)
CET_OFFSET = timedelta(hours=2)  # UTC+2

# Thresholds for alert
TEMP_THRESHOLD = 20  # Celsius, adjust as needed
RAIN_THRESHOLD = 0   # mm

# Fetch forecast (5-day / 3-hour)
url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&units=metric&appid={API_KEY}"
response = requests.get(url)
data = response.json()

if "list" not in data:
    print("Fel vid hämtning av prognos:", data)
    raise SystemExit("Ingen prognosdata hittades (kontrollera API-nyckel och endpoint)")

now_utc = datetime.utcnow()
alert_forecasts = []

# Check forecasts within next 3 hours
for forecast in data["list"]:
    forecast_time_utc = datetime.utcfromtimestamp(forecast["dt"])
    if forecast_time_utc > now_utc + timedelta(hours=3):
        break

    temp = forecast["main"]["temp"]
    rain = forecast.get("rain", {}).get("3h", 0)

    if temp < TEMP_THRESHOLD or rain > RAIN_THRESHOLD:
        forecast_time_local = forecast_time_utc + CET_OFFSET
        alert_forecasts.append((forecast_time_local, temp, rain))

if alert_forecasts:
    # Multi-recipient support
    recipients = [email.strip() for email in TO_EMAIL.split(",")]

    # Build message header
    if len(alert_forecasts) > 1:
        start_time = alert_forecasts[0][0].strftime('%H:%M')
        end_time = alert_forecasts[-1][0].strftime('%H:%M')
        header = f"⚠️ Vädret i Malmö (nästkommande 3h)\nMellan: {start_time}–{end_time}\nDetaljer:"
    else:
        header = "⚠️ Vädret i Malmö (nästkommande 3h)\nDetaljer:"

    # Build forecast lines
    messages = []
    for f_time, temp, rain in alert_forecasts:
        rain_msg = f", Regn: {rain} mm" if rain > 0 else ""
        messages.append(f"{f_time.strftime('%H:%M')} - Temp: {temp:.1f}°C{rain_msg}")

    alert_msg = header + "\n" + "\n".join(messages)

    # Prepare email
    msg = EmailMessage()
    msg.set_content(alert_msg)
    msg["Subject"] = "Vädervarning"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print("Varning skickad:\n", alert_msg)
else:
    print("Ingen regn- eller temperaturvarning för de kommande 3 timmarna.")
