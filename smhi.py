"""Väderlarm för Malmö via SMHI SNOW1gv1."""

import hashlib
import os
import pathlib
import smtplib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import requests

# Koordinaterna för platsen som väderprognosen gäller.
LAT = 55.593792
LON = 13.024406
# Hur långt fram i tiden vi söker efter vädervarningar.
ALERT_HOURS = 12
PRECIP_THRESHOLD = 0.0  # mm per prognosintervall
FROST_TEMP_THRESHOLD = 0.0
LOCAL_TZ = ZoneInfo("Europe/Stockholm")

# Inställningar för att skicka varningsmejl via Gmail.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
LAST_ALERT_FILE = pathlib.Path(".last_alert")

# Adress till SMHI:s prognostjänst.
API_URL = (
    "https://opendata-download-metfcst.smhi.se/api/category/snow1g/"
    f"version/1/geotype/point/lon/{LON}/lat/{LAT}/data.json"
)


# SMHI kan ange 9999 när ett mätvärde saknas.
def usable(value):
    return isinstance(value, (int, float)) and value != 9999


# Gå igenom prognosen och sammanställ varningar för de kommande timmarna.
def build_alerts(forecast):
    now = datetime.now(timezone.utc)
    until = now + timedelta(hours=ALERT_HOURS)
    alerts = defaultdict(lambda: defaultdict(list))

    # Undersök endast prognostillfällen inom den angivna tidsperioden.
    for period in forecast.get("timeSeries", []):
        valid_time = datetime.fromisoformat(period["time"].replace("Z", "+00:00"))
        if not now < valid_time <= until:
            continue

        values = period.get("data", {})
        temp = values.get("air_temperature")
        amount = values.get("precipitation_amount_mean")
        precip_type = values.get("predominant_precipitation_type_at_surface")

        # Visa tidpunkterna i svensk lokal tid.
        local = valid_time.astimezone(LOCAL_TZ)
        date_key, time_key = local.strftime("%Y-%m-%d"), local.strftime("%H:%M")
        messages = []

        if usable(temp) and temp <= FROST_TEMP_THRESHOLD:
            messages.append(f"🧊 Risk för frost ({temp:.1f} °C)")

        if usable(amount) and amount > PRECIP_THRESHOLD and usable(precip_type):
            # SNOW1gv1 använder andra kategorier än det gamla PMP3gv2.
            # 1=regn, 2=blandad nederbörd, 3=underkylt regn,
            # 5=snö, 6=underkyld blandad nederbörd, 11=duggregn.
            # Mängden är mm vattenekvivalent under prognosintervallet.
            start_raw = period.get("intervalParametersStartTime")
            duration = "prognosintervallet"
            if start_raw:
                start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                hours = (valid_time - start).total_seconds() / 3600
                if hours > 0:
                    duration = f"{hours:g} h"
            quantity = f"{amount:.1f} mm/{duration}"

            if precip_type == 3:
                messages.append(f"🧊 Underkylt regn ({quantity})")
            elif precip_type == 6:
                messages.append(f"🧊❄️ Underkyld blandad nederbörd ({quantity})")
            elif precip_type == 5:
                messages.append(f"❄️ Snö ({quantity} vattenekvivalent)")
            elif precip_type == 2:
                messages.append(f"❄️🌧️ Snöblandat regn ({quantity})")
            elif precip_type in (1, 11) and usable(temp) and -2 <= temp <= 2:
                messages.append(
                    f"⚠️ Regn nära fryspunkten ({quantity}, {temp:.1f} °C)"
                )

        if messages:
            alerts[date_key][time_key].extend(messages)

    # Sortera varningarna efter datum och klockslag för mejlet.
    lines = []
    for date_key in sorted(alerts):
        lines.append(date_key)
        for time_key in sorted(alerts[date_key]):
            lines.append(f"  {time_key}: {' och '.join(alerts[date_key][time_key])}")
        lines.append("")
    return "\n".join(lines).strip()


# Hämta prognosen och skicka mejl när nya varningar finns.
def main():
    print(f"Hämtar prognos från SMHI: {API_URL}")
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    forecast = response.json()
    if not forecast.get("timeSeries"):
        raise ValueError("SMHI returnerade ingen prognosserie")

    alert_text = build_alerts(forecast)
    last_hash = LAST_ALERT_FILE.read_text().strip() if LAST_ALERT_FILE.exists() else None
    if not alert_text:
        print("Inga varningar under de kommande 12 timmarna.")
        LAST_ALERT_FILE.write_text("")
        return

    # Jämför med föregående varning för att undvika identiska mejl.
    alert_hash = hashlib.sha256(alert_text.encode("utf-8")).hexdigest()
    if alert_hash == last_hash:
        print("Oförändrad prognos, skickar inget nytt mejl.")
        return

    # Läs e-postuppgifterna från miljövariabler/GitHub Secrets.
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    recipients_raw = os.getenv("TO_EMAIL", "")
    recipients = [address.strip() for address in recipients_raw.split(",") if address.strip()]
    if not sender or not password or not recipients:
        raise ValueError("EMAIL_ADDRESS, EMAIL_PASSWORD eller TO_EMAIL saknas i GitHub Secrets")

    message = EmailMessage()
    message["Subject"] = "Vädervarning – Malmö"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content("Vädervarningar för Malmö, kommande 12 timmar:\n\n" + alert_text)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)

    # Spara först när mejlet verkligen har skickats.
    LAST_ALERT_FILE.write_text(alert_hash)
    print("Mejl skickat:\n" + alert_text)


if __name__ == "__main__":
    main()
