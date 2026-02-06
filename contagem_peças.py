import cv2
from pyzbar import pyzbar
import psycopg2
import urllib.parse
from datetime import datetime
import time
import numpy as np

# ----------------------------------------------------------------------
# CONFIGURAÇÕES
# ----------------------------------------------------------------------
DATABASE_URL = "postgresql://contagem_pecas_user:tNaqE77LPjDETlvsJVtbB902R3oAvTFh@dpg-d62usc4r85hc739tpvp0-a.oregon-postgres.render.com/contagem_pecas"

JANELA_DUP_SEG = 3
ultimas_leituras = {}

# Parse da URL do banco
result = urllib.parse.urlparse(DATABASE_URL)
host = result.hostname
database = result.path[1:]
username = result.username
password = result.password
port = result.port

# Seus produtos
produtos = [
    ("9133901004013", "TANGA FIO DUPLO BELA FLOR", "PP", "PRETO"),
    ("9133901004174", "TANGA FIO DUPLO BELA FLOR", "PP", "DIVINO"),
]

dicionario_produtos = {codigo: (modelo, tamanho, cor) for codigo, modelo, tamanho, cor in produtos}

def conectar_banco():
    return psycopg2.connect(host=host, database=database, user=username, password=password, port=port)

def salvar_peca(modelo, tamanho, cor):
    """Salva 1 peça no banco."""
    conn = conectar_banco()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO contagem (modelo, tamanho, cor, contagem, data)
        VALUES (%s, %s, %s, 1, %s)
    """, (modelo, tamanho, cor, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    cur.close()
    conn.close()

def main():
    print("🎥 Leitor de Código de Barras - PC LOCAL")
    print("Produtos cadastrados:")
    for codigo, (modelo, tamanho, cor) in dicionario_produtos.items():
        print(f"  {codigo}: {modelo} - {tamanho} - {cor}")
    print("-" * 50)
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
    
    print("Aponte a câmera! Pressione 'q' para sair...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Detectar códigos
        barcodes = pyzbar.decode(frame)
        codigo_ok = None
        
        for barcode in barcodes:
            codigo = barcode.data.decode('utf-8')
            if codigo in dicionario_produtos:
                codigo_ok = codigo
                # Desenhar retângulo VERDE
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                break
        
        # Registrar se código válido e não duplicata
        if codigo_ok:
            agora = time.time()
            if codigo_ok not in ultimas_leituras or agora - ultimas_leituras[codigo_ok] > JANELA_DUP_SEG:
                ultimas_leituras[codigo_ok] = agora
                
                modelo, tamanho, cor = dicionario_produtos[codigo_ok]
                salvar_peca(modelo, tamanho, cor)
                
                print(f"✅ {datetime.now().strftime('%H:%M:%S')} | {modelo} - {tamanho} - {cor}")
        
        # Mostrar frame
        cv2.imshow("Leitor de Códigos - PC LOCAL", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("👋 Leitor encerrado.")

if __name__ == "__main__":
    main()