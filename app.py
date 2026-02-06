import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Dashboard Contagem de Peças", layout="wide")

st.title("📊 Dashboard Contagem de Peças")

# ----------------------------------------------------------------------
# 1) AQUI VOCÊ VAI COLOCAR A URL DO BANCO DO RENDER
# ----------------------------------------------------------------------
DATABASE_URL = "postgresql://contagem_pecas_user:tNaqE77LPjDETlvsJVtbB902R3oAvTFh@dpg-d62usc4r85hc739tpvp0-a.oregon-postgres.render.com/contagem_pecas"

# PARSE A URL DO BANCO
result = urllib.parse.urlparse(DATABASE_URL)
host = result.hostname
database = result.path[1:]
username = result.username
password = result.password
port = result.port

# ----------------------------------------------------------------------
# 2) CONECTAR AO POSTGRESQL
# ----------------------------------------------------------------------
try:
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=username,
        password=password,
        port=port
    )
    st.success("✅ Conexão com o banco de dados estabelecida!")
except Exception as e:
    st.error(f"❌ Erro ao conectar com o banco: {e}")
    st.stop()

# ----------------------------------------------------------------------
# 3) CRIAR TABELA DE CONTAGEM (SE NÃO EXISTIR)
# ----------------------------------------------------------------------
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS contagem (
        modelo TEXT,
        tamanho TEXT,
        cor TEXT,
        contagem INTEGER,
        data TEXT
    )
""")
conn.commit()

# ----------------------------------------------------------------------
# 4) CARREGAR OS DADOS DO BANCO
# ----------------------------------------------------------------------
try:
    df = pd.read_sql_query("SELECT * FROM contagem", conn)
    conn.close()
except Exception as e:
    st.error(f"❌ Erro ao carregar dados: {e}")
    df = pd.DataFrame()

if df.empty:
    st.warning("Nenhuma contagem registrada ainda.")
else:
    # ----------------------------------------------------------------------
    # 5) KPIs (indicadores)
    # ----------------------------------------------------------------------
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Peças", df["contagem"].sum())
    col1.metric("👕 Modelos", df["modelo"].nunique())
    col2.metric("📅 Última Atual.", df["data"].max())
    col3.metric("📉 Linhas", len(df))

    # ----------------------------------------------------------------------
    # 6) GRÁFICO DE BARRAS POR MODELO
    # ----------------------------------------------------------------------
    df_modelo = df.groupby("modelo")["contagem"].sum().reset_index()
    fig1 = px.bar(df_modelo, x="modelo", y="contagem", title="Contagem por Modelo", color="contagem")
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

    # ----------------------------------------------------------------------
    # 7) GRÁFICO DE BARRAS POR TAMANHO
    # ----------------------------------------------------------------------
    df_tamanho = df.groupby("tamanho")["contagem"].sum().reset_index()
    fig2 = px.bar(df_tamanho, x="tamanho", y="contagem", title="Contagem por Tamanho", color="contagem")
    fig2.update_layout(showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

    # ----------------------------------------------------------------------
    # 8) TABELA DETALHADA
    # ----------------------------------------------------------------------
    st.subheader("📋 Detalhes da Contagem")
    st.dataframe(df)