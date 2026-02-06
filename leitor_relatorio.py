import schedule
import time
from datetime import datetime
import pywhatkit as pwk
from contagem_peças import totais_dia, hoje

NUMERO_GERENTE = "+5532999751615" 
HOJE = datetime.now().strftime("%Y-%m-%d")
TOTALS = {}

def enviar_20h():
    total = sum(totais_dia.get(hoje, {}).values())
    msg = f"📦 {hoje}\nTotal: {total} peças\n"
    for m, q in totais_dia.get(hoje, {}).items():
        msg += f"{m}: {q}\n"
    pywhatkit.sendwhatmsg_instantly(NUMERO_GERENTE, msg)
    print("📱 Enviado!")

schedule.every().day.at("20:00").do(enviar_20h)

while True:
    schedule.run_pending()
    time.sleep(60)