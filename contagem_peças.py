import cv2
from pyzbar.pyzbar import decode
import numpy as np
import psycopg2
import urllib.parse
from datetime import datetime
import time

# ----------------------------------------------------------------------
# 1) CONFIGURAÇÕES
# ----------------------------------------------------------------------
DATABASE_URL = "postgresql://contagem_pecas_user:tNaqE77LPjDETlvsJVtbB902R3oAvTFh@dpg-d62usc4r85hc739tpvp0-a.oregon-postgres.render.com/contagem_pecas"

JANELA_DUP_SEG = 3  # segundos para evitar duplicatas
ultimas_leituras = {}  # codigo_barra: timestamp

# Parse da URL do banco
result = urllib.parse.urlparse(DATABASE_URL)
host = result.hostname
database = result.path[1:]
username = result.username
password = result.password
port = result.port

# ----------------------------------------------------------------------
# 2) SEUS PRODUTOS (tupla: código, modelo, tamanho, cor)
# ----------------------------------------------------------------------
produtos = [
    ("9133901004013", "TANGA FIO DUPLO BELA FLOR", "PP", "PRETO"),
    ("9133901004174", "TANGA FIO DUPLO BELA FLOR", "PP", "DIVINO"),
]

# Dicionário para buscar produto pelo código de barras
dicionario_produtos = {}
for codigo, modelo, tamanho, cor in produtos:
    dicionario_produtos[codigo] = (modelo, tamanho, cor)

# Contagem de peças
contagem = {}


# ----------------------------------------------------------------------
# 3) FUNÇÕES
# ----------------------------------------------------------------------
def evitar_duplicata(codigo: str, agora: float) -> bool:
    """Retorna True se deve aceitar a peça (não é duplicata recente)."""
    if codigo not in ultimas_leituras:
        ultimas_leituras[codigo] = agora
        return True

    ultima = ultimas_leituras[codigo]
    if agora - ultima >= JANELA_DUP_SEG:
        ultimas_leituras[codigo] = agora
        return True

    return False


def decodificar_barcodes(frame):
    """Decodifica códigos de barras em um frame e retorna o código se houver."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)

    if barcodes:
        # pega o primeiro código encontrado
        codigo_bytes = barcodes[0].data
        codigo_str = codigo_bytes.decode("utf-8")
        return codigo_str, barcodes[0]
    return None, None


def destacar_barcode(frame, barcode):
    """Desenha caixa, dados e texto no frame."""
    (x, y, w, h) = barcode.rect
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    dados = barcode.data.decode("utf-8")
    tipo = barcode.type

    texto = f"{dados} ({tipo})"
    cv2.putText(
        frame,
        texto,
        (x, y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2,
    )

    # Se o código já foi contabilizado, mostra “OK”
    if dados in dicionario_produtos:
        modelo, tamanho, cor = dicionario_produtos[dados]
        chave = (dados, modelo, tamanho, cor)
        total = contagem.get(chave, 0)
        linha = f"{modelo} - {tamanho} - {cor} | {total + 1}"
        cv2.putText(
            frame,
            f"Contagem: {linha}",
            (x, y + h + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            2,
        )


def registrar_contagem(codigo: str):
    """Atualiza `contagem` se o código for válido e não for duplicata recente."""
    if codigo not in dicionario_produtos:
        print(f"⚠ Código inválido ou não cadastrado: {codigo}")
        return

    agora = time.time()
    if not evitar_duplicata(codigo, agora):
        return

    modelo, tamanho, cor = dicionario_produtos[codigo]
    chave = (codigo, modelo, tamanho, cor)
    contagem[chave] = contagem.get(chave, 0) + 1

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"✅ {ts} | {modelo} - {tamanho} - {cor} | Total: {contagem[chave]} peça(s)")


def conectar_banco():
    """Conecta ao PostgreSQL e retorna a conexão (opcional, só exemplo)."""
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=username,
            password=password,
            port=port,
        )
        print("🟢 Conectado ao banco PostgreSQL.")
        return conn
    except Exception as e:
        print(f"🔴 Erro ao conectar ao banco: {e}")
        return None


def salvar_contagem_no_banco(conn):
    """Função de exemplo: salva contagem em uma tabela (ajuste o nome da tabela e campos)."""
    if not conn:
        return

    cursor = conn.cursor()
    try:
        # Exemplo de tabela: contagem_pecas(codigo, modelo, tamanho, cor, total, horario)
        cursor.execute("""
            DROP TABLE IF EXISTS contagem_pecas;
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contagem_pecas (
                id SERIAL PRIMARY KEY,
                codigo_barra VARCHAR(50),
                modelo VARCHAR(100),
                tamanho VARCHAR(20),
                cor VARCHAR(50),
                total INT,
                horario TIMESTAMP
            );
        """)

        dt = datetime.now()
        for (codigo, modelo, tamanho, cor), total in contagem.items():
            cursor.execute("""
                INSERT INTO contagem_pecas
                    (codigo_barra, modelo, tamanho, cor, total, horario)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (codigo, modelo, tamanho, cor, total, dt))

        conn.commit()
        print("💾 Contagem salva no banco.")
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")
        conn.rollback()
    finally:
        cursor.close()


# ----------------------------------------------------------------------
# 4) EXECUÇÃO PRINCIPAL
# ----------------------------------------------------------------------
def main():
    print("=== Contagem de Peças com Código de Barras ===")
    print("Produto cadastrado:")
    for codigo, modelo, tamanho, cor in produtos:
        print(f"  {codigo}: {modelo} - {tamanho} - {cor}")
    print("-" * 60)

    # # Conexão ao banco (opcional)
    # conn = conectar_banco()
    # if not conn:
    #     print("Continuando sem banco de dados...")

    # Webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

    if not cap.isOpened():
        print("❌ Falha ao abrir a webcam.")
        return

    print("💡 Aponte o código de barras para a câmera para escanear...")
    print("Pressione 'q' para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Erro ao ler o frame da câmera.")
            break

        codigo, barcode = decodificar_barcodes(frame)

        if codigo:
            registrar_contagem(codigo)
            if barcode:
                destacar_barcode(frame, barcode)

        # Mostra o frame
        cv2.imshow("Leitor de Código de Barras", frame)

        # Q to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Ao sair
    cap.release()
    cv2.destroyAllWindows()
    print("Encerrando o programa...")

    # Exibir contagem final
    print("\n📈 Contagem final:")
    for (codigo, modelo, tamanho, cor), total in contagem.items():
        print(f"  {codigo} | {modelo} - {tamanho} - {cor} | {total} peças")

    # Exemplo de salvar no banco (se habilitar)
    # salvar_contagem_no_banco(conn)
    # if conn:
    #     conn.close()


if __name__ == "__main__":
    main()