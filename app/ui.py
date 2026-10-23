import os
import subprocess
import threading
import time
import uuid

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from app.core.observability import log_consolidated_metric, log_ui_event

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

# --- Inicialização do Estado de Navegação ---
if "current_cursor" not in st.session_state:
    st.session_state["current_cursor"] = None
if "cursor_history" not in st.session_state:
    st.session_state["cursor_history"] = []
if "search_results" not in st.session_state:
    st.session_state["search_results"] = None
if "last_query_params" not in st.session_state:
    st.session_state["last_query_params"] = {}

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

    limit = st.slider("Resultados por página", 20, 100, 20)

    buscar = st.button("🚀 Pesquisar")


# Função para realizar a busca
def perform_search(cursor=None):
    interaction_id = str(uuid.uuid4())
    t0_interaction = time.perf_counter()

    params = {
        "uf": uf if uf else None,
        "municipio": municipio if municipio else None,
        "cnae": cnae if cnae else None,
        "ativa": ativa,
        "com_telefone": com_telefone,
        "com_email": com_email,
        "limit": limit,
        "cursor": cursor,
    }

    # Verifica se os filtros mudaram para resetar a navegação
    current_filters = {k: v for k, v in params.items() if k != "cursor"}
    if st.session_state["last_query_params"] != current_filters:
        st.session_state["cursor_history"] = []
        st.session_state["current_cursor"] = None
        st.session_state["last_query_params"] = current_filters
        params["cursor"] = None

        log_ui_event(
            {
                "event": "search_started",
                "interaction_id": interaction_id,
                "params": {k: v for k, v in params.items() if k != "cursor"},
                "has_cursor": bool(cursor),
            }
        )

    # attempt = 1
    response = None
    error_stage = None
    error_class = None

    try:
        t0_http = time.perf_counter()
        request_id = interaction_id  # Usando o mesmo ID para correlação inicial
        headers = {"X-Request-ID": request_id}

        try:
            with st.spinner("Consultando base DuckDB no R2..."):
                response = requests.get(
                    f"{API_URL}/busca", params=params, headers=headers, timeout=30
                )
            t1_http = time.perf_counter()
            http_duration_ms = round((t1_http - t0_http) * 1000, 2)

            status_code = response.status_code

            if status_code == 200:
                st.session_state["search_results"] = response.json()
                st.session_state["current_cursor"] = cursor

                t1_interaction = time.perf_counter()
                total_e2e_ms = round((t1_interaction - t0_interaction) * 1000, 2)
                streamlit_processing_ms = round(
                    max(total_e2e_ms - http_duration_ms, 0), 2
                )

                # Registro consolidado final da busca (Ponto de vista da UI)
                log_consolidated_metric(
                    "search_completed",
                    interaction_id=interaction_id,
                    request_id=request_id,
                    result="success",
                    search={k: v for k, v in params.items() if k != "cursor"},
                    metrics={
                        "total_e2e_ms": total_e2e_ms,
                        "http_request_ms": http_duration_ms,
                        "streamlit_processing_ms": max(streamlit_processing_ms, 0.1),
                    },
                )
            else:
                error_stage = "api_error"
                st.error(f"Erro na API: {response.text}")
                log_ui_event(
                    {
                        "event": "search_failed",
                        "interaction_id": interaction_id,
                        "request_id": request_id,
                        "error_stage": error_stage,
                        "status_code": status_code,
                    }
                )

        except requests.exceptions.RequestException as e:
            t1_http = time.perf_counter()
            http_duration_ms = round((t1_http - t0_http) * 1000, 2)
            error_stage = "http_request"
            error_class = type(e).__name__
            st.error(f"Falha na conexão com o servidor: {e}")
            log_ui_event(
                {
                    "event": "search_failed",
                    "interaction_id": interaction_id,
                    "request_id": request_id,
                    "error_stage": error_stage,
                    "error_class": error_class,
                    "metrics": {"http_request_ms": http_duration_ms},
                }
            )

    except Exception as e:  # noqa: BLE001
        error_stage = "ui_processing"
        error_class = type(e).__name__
        st.error(f"Erro inesperado na interface: {e}")
        log_ui_event(
            {
                "event": "search_failed",
                "interaction_id": interaction_id,
                "error_stage": error_stage,
                "error_class": error_class,
            }
        )


# Lógica de gatilho de busca
if buscar:
    perform_search(cursor=None)

# Exibição de Resultados e Navegação
if st.session_state["search_results"]:
    data = st.session_state["search_results"]

    if data["data"]:
        df = pd.DataFrame(data["data"])
        st.dataframe(df, use_container_width=True)

        # Controles de Paginação
        col_prev, col_page, col_next = st.columns([1, 2, 1])

        with col_prev:
            if st.button("⬅️ Anterior", disabled=not st.session_state["cursor_history"]):
                prev_cursor = st.session_state["cursor_history"].pop()
                perform_search(cursor=prev_cursor)
                st.rerun()

        with col_page:
            current_page = len(st.session_state["cursor_history"]) + 1
            st.markdown(
                f"<p style='text-align: center;'>Página {current_page}</p>",
                unsafe_allow_html=True,
            )

        with col_next:
            next_cursor = data.get("next_cursor")
            if st.button("Próxima ➡️", disabled=not next_cursor):
                st.session_state["cursor_history"].append(
                    st.session_state["current_cursor"]
                )
                perform_search(cursor=next_cursor)
                st.rerun()

        # Botões de Exportação (opcional/futuro)
        st.markdown("---")
        col1, col2 = st.columns(2)
        # with col1:
        # st.markdown("### 📥 Exportar Resultados")
        # st.info("Baixa os primeiros 10.000 registros filtrados")
        # ... lógica de exportação ...
    else:
        st.warning("Nenhuma empresa encontrada com esses filtros.")
else:
    if not buscar:
        st.info("Use os filtros na barra lateral e clique em Pesquisar para começar.")
