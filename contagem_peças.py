import cv2
from pyzbar import pyzbar
import psycopg2
import urllib.parse
from datetime import datetime
import time
import numpy as np

DATABASE_URL = "postgresql://contagem_pecas_user:tNaqE77LPjDETlvsJVtbB902R3oAvTFh@dpg-d62usc4r85hc739tpvp0-a.oregon-postgres.render.com/contagem_pecas"

JANELA_DUP_SEG = 3
ultimas_leituras = {}
hoje = datetime.now().strftime("%Y-%m-%d")
totais_dia = {}

result = urllib.parse.urlparse(DATABASE_URL)
host, database, username, password, port = result.hostname, result.path[1:], result.username, result.password, result.port

produtos = [
    ("9133901004013", "TANGA FIO DUPLO BELA FLOR", "PP", "PRETO"),
    ("9133901004174", "TANGA FIO DUPLO BELA FLOR", "PP", "DIVINO"),
]

dicionario_produtos = {codigo: (modelo, tamanho, cor) for codigo, modelo, tamanho, cor in produtos}

def conectar_banco():
    return psycopg2.connect(host=host, database=database, user=username, password=password, port=port)

def inicializar_banco():  # ← NOVA FUNÇÃO
    conn = conectar_banco()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS contagem (modelo TEXT, tamanho TEXT, cor TEXT, contagem INTEGER, data TEXT)")
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM contagem")
    if cur.fetchone()[0] == 0:
        teste = [
            ("TANGA FIO DUPLO BELA FLOR", "PP", "PRETO", 15, "2026-02-06 09:15"),
            ("TANGA FIO DUPLO BELA FLOR", "PP", "DIVINO", 8, "2026-02-06 10:30"),
        ]
        for row in teste:
            cur.execute("INSERT INTO contagem VALUES (%s,%s,%s,%s,%s)", row)
        conn.commit()
        print("✅ Tabela criada + teste OK!")
    
    cur.close()
    conn.close()

def salvar_peca(modelo, tamanho, cor):
    conn = conectar_banco()
    cur = conn.cursor()
    cur.execute("INSERT INTO contagem (modelo, tamanho, cor, contagem, data) VALUES (%s,%s,%s,1,%s)", 
                (modelo, tamanho, cor, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    cur.close()
    conn.close()
    
    global totais_dia, hoje
    modelo_key = modelo.replace(" ", "_")[:15]
    if hoje not in totais_dia: totais_dia[hoje] = {}
    totais_dia[hoje][modelo_key] = totais_dia[hoje].get(modelo_key, 0) + 1

def main():
    inicializar_banco()  # ← 1x só!
    
    print("🎥 Leitor...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        barcodes = pyzbar.decode(frame)
        for barcode in barcodes:
            codigo = barcode.data.decode('utf-8')
            if codigo in dicionario_produtos:
                agora = time.time()
                if codigo not in ultimas_leituras or agora - ultimas_leituras[codigo] > JANELA_DUP_SEG:
                    ultimas_leituras[codigo] = agora
                    modelo, tamanho, cor = dicionario_produtos[codigo]
                    salvar_peca(modelo, tamanho, cor)
                    cv2.rectangle(frame, barcode.rect, (0,255,0), 3)
        
        # CONTADOR TELA
        total_dia = sum(totais_dia.get(hoje, {}).values())
        cv2.putText(frame, f"HOJE {hoje}: {total_dia}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imshow("Leitor", frame)
        
        if cv2.waitKey(1) == ord('q'): break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()