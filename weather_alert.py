import os
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, date

# ======================
# CONFIGURATION
# ======================
API_KEY = os.getenv("OPENWEATHER_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")  # comma-separated emails

LAT, LON = 55.593792, 13.024406  # Spånehusvägen 87, Malmö
CET_OFFSET = timedelta(hours=2)   # UTC+2 (CEST in summer)
TEMP_THRESHOLD = 20               # Celsius
RAIN_THRESHOLD = 0                # mm
ALERT_FILE = "last_alert.txt"     # file to store last alert date

# ======================
# CHECK IF ALERT ALREADY SENT TODAY
# ======================
today_str = date.today().isoformat()
if os.path.exists(ALERT_FILE):
    with open(ALERT_FILE, "r") as f:
        last_date = f.read().strip()
    if last_date == today_str:
        print("Varning redan skickad idag, hoppar över.")
        exit()

# ======================
# FETCH FORECAST
# ======================
url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&units=metric&appid={API_KEY}"
response = requests.get(url)
data = response.json()

if "list" not in data:
    print("Fel vid hämtning av prognos:", data)
    raise SystemExit("Ingen prognosdata hittades (kontrollera API-nyckel och endpoint)")

now_utc = datetime.utcnow()
alert_forecasts = []

# ======================
# CHECK NEXT 3 HOURS
# ======================
for forecast in data["list"]:
    forecast_time_utc = datetime.utcfromtimestamp(forecast["dt"])
    if forecast_time_utc > now_utc + timedelta(hours=3):
        break

    temp = forecast["main"]["temp"]
    rain = forecast.get("rain", {}).get("3h", 0)

    if temp < TEMP_THRESHOLD or rain > RAIN_THRESHOLD:
        forecast_time_local = forecast_time_utc + CET_OFFSET
        alert_forecasts.append((forecast_time_local, temp, rain))

# ======================
# SEND ALERT IF ANY
# ======================
if alert_forecasts:
    # Prepare recipients
    recipients = [email.strip() for email in TO_EMAIL.split(",") if email.strip()]

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
        # Show "Nu" if it's the current hour
        time_label = "Nu" if abs((f_time - (now_utc + CET_OFFSET)).total_seconds()) < 3600 else f_time.strftime('%H:%M')
        rain_msg = f", Regn: {rain} mm" if rain > 0 else ""
        messages.append(f"{time_label} - Temp: {temp:.1f}°C{rain_msg}")

    alert_msg = header + "\n" + "\n".join(messages)

    # Prepare email
    msg = EmailMessage()
    msg.set_content(alert_msg)
    msg["Subject"] = "Vädervarning"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)  # display only

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg, from_addr=EMAIL_ADDRESS, to_addrs=recipients)

    # Save today's date
    with open(ALERT_FILE, "w") as f:
        f.write(today_str)

    print("Varning skickad:\n", alert_msg)
else:
    print("Ingen regn- eller temperaturvarning för de kommande 3 timmarna.")
