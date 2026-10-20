import os
import subprocess
import threading
import time

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Configurações
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")
R2_REMOTE = "r2:buscafri-data"

st.set_page_config(page_title="BuscaFri - Analytics CNPJ", layout="wide")


# --- Monitoramento R2 em Background ---
def r2_keep_alive():
    """Roda em loop para manter a conexão com o R2 ativa via rclone"""
    rclone_bin = "rclone" if os.name != "nt" else "rclone.exe"
    while True:
        try:
            # Comando leve para manter a conexão quente
            subprocess.run(
                [rclone_bin, "lsf", R2_REMOTE, "--max-depth", "1"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except Exception:  # noqa: S110, BLE001
            pass
        time.sleep(5)


# Inicia o monitor apenas uma vez
if "monitor_started" not in st.session_state:
    threading.Thread(target=r2_keep_alive, daemon=True).start()
    st.session_state["monitor_started"] = True

# --- Interface Streamlit ---
st.title("🏢 BuscaFri - Consulta & Analytics CNPJ")
st.markdown("---")

# Sidebar com filtros
with st.sidebar:
    st.header("🔍 Filtros de Busca")
    uf = st.selectbox(
        "Estado (UF)",
        [
            "",
            "AC",
            "AL",
            "AM",
            "AP",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MG",
            "MS",
            "MT",
            "PA",
            "PB",
            "PE",
            "PI",
            "PR",
            "RJ",
            "RN",
            "RO",
            "RR",
            "RS",
            "SC",
            "SE",
            "SP",
            "TO",
        ],
    )
    municipio = st.text_input("Código Município (opcional)")
    cnae = st.text_input("Código CNAE (opcional)")

    st.subheader("Configurações")
    ativa = st.checkbox("Apenas empresas Ativas", value=True)
    com_telefone = st.checkbox("Possui Telefone")
    com_email = st.checkbox("Possui E-mail")

    limit = st.slider("Resultados por página", 10, 100, 20)

    buscar = st.button("🚀 Pesquisar")

# Área principal
if buscar:
    params = {
        "uf": uf if uf else None,
        "municipio": municipio if municipio else None,
        "cnae": cnae if cnae else None,
        "ativa": ativa,
        "com_telefone": com_telefone,
        "com_email": com_email,
        "limit": limit,
    }

    try:
        with st.spinner("Consultando base DuckDB no R2..."):
            response = requests.get(f"{API_URL}/busca", params=params)

        if response.status_code == 200:
            data = response.json()
            # st.success(f"Encontrados {data['total_count']} registros!")

            if data["data"]:
                df = pd.DataFrame(data["data"])
                st.dataframe(df, use_container_width=True)

                # Botões de Exportação
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 📥 Exportar Resultados")
                    st.info("Baixa os primeiros 10.000 registros filtrados")

                    csv_url = f"{API_URL}/exportar/csv"
                    xlsx_url = f"{API_URL}/exportar/xlsx"

                    # Gerar links de download direto da API
                    # Nota: Em streamlit, links diretos funcionam melhor que st.download_button para streaming pesado
                    # st.markdown(f"[📄 Baixar CSV]({csv_url})")
                    # st.markdown(f"[📊 Baixar Excel]({xlsx_url})")
            else:
                st.warning("Nenhuma empresa encontrada com esses filtros.")
        else:
            st.error(f"Erro na API: {response.text}")

    except Exception as e:  # noqa: BLE001
        st.error(f"Falha na conexão com o servidor: {e}")
else:
    st.info("Use os filtros na barra lateral e clique em Pesquisar para começar.")
    # st.image("https://buscafri.com.br/logo.png", width=200)  # Exemplo de logo
