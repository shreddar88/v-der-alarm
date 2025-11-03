import os
import requests
import smtplib
from email.message import EmailMessage

API_KEY = os.getenv("076814283aaedd338f506cf4f0182fa8")
EMAIL_ADDRESS = os.getenv("shreddar88@gmail.com")
EMAIL_PASSWORD = os.getenv("nxnn zmhv zsir mvdh")
TO_EMAIL = os.getenv("shreddar88@gmail.com")

CITY = "Malmo,SE"
URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"

response = requests.get(URL)
weather = response.json()

temp = weather["main"]["temp"]
rain = "rain" in weather

if temp < 0 or rain:
    alert = f"⚠️ Weather Alert for {CITY}: {temp}°C and rain={rain}"
    
    msg = EmailMessage()
    msg.set_content(alert)
    msg["Subject"] = "Weather Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
        
    print("Alert sent:", alert)
else:
    print("No alert: temperature and rain are normal.")
