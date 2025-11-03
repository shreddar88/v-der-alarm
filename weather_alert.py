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
weather = response.json()

temp = weather["main"]["temp"]
rain = "rain" in weather
if temp < 0 or rain:
#if temp < 15 or rain:
    alert = f"⚠️ Temperatur i Malmö {temp}°C och sannolikhet för regn={rain}"
    msg = EmailMessage()
    msg.set_content(alert)
    msg["Subject"] = "Väder varning, snöröjargänget"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
        
    print("Alert sent:", alert)
else:
    print("No alert: temperature and rain are normal.")
