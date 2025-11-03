import os
import requests
import smtplib
from email.message import EmailMessage

API_KEY = os.getenv("OPENWEATHER_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

LAT, LON = 55.6050, 13.0038 # Malmö coordinates
URL = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
#CITY = "Malmo,SE"
#URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"

response = requests.get(URL)
data = response.json(
    
alert_needed = False
alert_time = None
alert_temp = None

# Check next 3 hours
now = datetime.utcnow()
for forecast in data["list"]:
    forecast_time = datetime.utcfromtimestamp(forecast["dt"])
    if forecast_time > now + timedelta(hours=3):
        break
    rain = forecast.get("rain", {}).get("3h", 0)
    temp = forecast["main"]["temp"]
    if temp < 0 or rain > 0:
        alert_needed = True
        alert_time = forecast_time
        alert_temp = temp
        break

if alert_needed:
    local_time = alert_time + timedelta(hours=2)  # convert UTC to CET
    alert_msg = f"⚠️ Weather Alert for Malmö:\nTemperature: {alert_temp}°C\nRain expected at: {local_time.strftime('%H:%M')}"
    
    msg = EmailMessage()
    msg.set_content(alert_msg)
    msg["Subject"] = "Weather Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    
    print("Alert sent:", alert_msg)
else:
    print("No alert in the next 3 hours.")
    
#data = response.json()
#temp = data["main"]["temp"]
#rain_mm = data.get("rain", {}).get("1h", 0)
#alert_needed = temp < 0 or rain_mm > 0
#if alert_needed:
 #   alert_msg = f"⚠️ Weather Alert for Malmö:\nTemperature: {temp}°C\nRain volume: {rain_mm} mm"
    
  #  msg = EmailMessage()
  #  msg.set_content(alert_msg)
  #  msg["Subject"] = "Weather Alert"
  #  msg["From"] = EMAIL_ADDRESS
  #  msg["To"] = TO_EMAIL
   #  with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
 #       smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
  #      smtp.send_message(msg)
 #    print("Alert sent:", alert_msg)
#else:
 #   print(f"No alert. Temp: {temp}°C, Rain volume: {rain_mm} mm")
    
#weather = response.json()

#temp = weather["main"]["temp"]
#rain = "rain" in weather
#if temp < 0 or rain:
#if temp < 15 or rain:
 #   alert = f"⚠️ Temperatur i Malmö {temp}°C och sannolikhet för regn={rain}"
  #  msg = EmailMessage()
   # msg.set_content(alert)
    #msg["Subject"] = "Väder varning, snöröjargänget"
    #msg["From"] = EMAIL_ADDRESS
    #msg["To"] = TO_EMAIL
    
    #with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
     #   smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
     #   smtp.send_message(msg)
        
    #print("Alert sent:", alert)
#else:
 #   print("No alert: temperature and rain are normal.")
