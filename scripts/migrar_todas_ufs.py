from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import duckdb
from dotenv import load_dotenv

# Raiz do projeto: diretório pai de scripts/
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

# Carrega explicitamente o .env da raiz
ARQUIVO_ENV = RAIZ_PROJETO / ".env"
load_dotenv(ARQUIVO_ENV, override=False)

# Confirma que o arquivo existe sem mostrar credenciais
if not ARQUIVO_ENV.is_file():
    raise FileNotFoundError(f"Arquivo .env não encontrado: {ARQUIVO_ENV}")

account_id = os.getenv("R2_ACCOUNT_ID")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

if not account_id or not access_key or not secret_key:
    raise ValueError(
        "Credenciais incompletas no .env. "
        "Verifique R2_ACCOUNT_ID, R2_ACCESS_KEY_ID "
        "e R2_SECRET_ACCESS_KEY."
    )

DIRETORIO_REORDENADO = RAIZ_PROJETO / "data" / "reordenado" / "estabelecimentos"

DIRETORIO_ORIGINAL = RAIZ_PROJETO / "data" / "particionado" / "estabelecimentos"

ARQUIVO_RELATORIO = RAIZ_PROJETO / "data" / "relatorios" / "auditoria_r2.json"

"""
UFS = [
    "SP",
]
"""
UFS = [
    "SP",
]


resultados: list[dict[str, Any]] = []

BUCKET = os.getenv("R2_BUCKET_NAME", "buscafri-data").strip()

if not BUCKET:
    raise ValueError("A variável R2_BUCKET_NAME está vazia ou não está configurada.")

REMOTE_ROOT = f"r2:{BUCKET}/estabelecimentos"
# ============================================================
# RELATÓRIO
# ============================================================


def registrar(
    uf: str,
    status: str,
    detalhe: str,
    registros: int | None = None,
    tamanho_bytes: int | None = None,
    remoto_anterior: int | None = None,
) -> None:
    """Adiciona o resultado de uma UF ao relatório da execução."""

    resultado = {
        "uf": uf,
        "status": status,
        "detalhe": detalhe,
        "registros_locais": registros,
        "registros_remotos_anteriores": remoto_anterior,
        "tamanho_local_bytes": tamanho_bytes,
        "data_hora": datetime.now().astimezone().isoformat(),
    }

    resultados.append(resultado)
    print(f"[{uf}] {status}: {detalhe}")


def salvar_relatorio() -> None:
    """Salva o relatório consolidado em JSON."""

    ARQUIVO_RELATORIO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resumo = {
        "projeto": "BuscaFri",
        "bucket": BUCKET,
        "data_hora": datetime.now().astimezone().isoformat(),
        "total_ufs": len(UFS),
        "processadas": len(resultados),
        "atualizadas": sum(item["status"] == "PUBLICADA" for item in resultados),
        "ja_atualizadas": sum(item["status"] == "JA ATUALIZADA" for item in resultados),
        "falhas": sum(item["status"] == "FALHA" for item in resultados),
        "resultados": resultados,
    }

    ARQUIVO_RELATORIO.write_text(
        json.dumps(
            resumo,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nRelatório salvo em: {ARQUIVO_RELATORIO}")


# ============================================================
# DUCKDB / CLOUDFLARE R2
# ============================================================


def configurar_duckdb() -> duckdb.DuckDBPyConnection:
    """Inicializa o DuckDB com limites de memória, threads e diretório temporário, e configura o acesso ao Cloudflare R2."""

    load_dotenv(RAIZ_PROJETO / ".env")

    max_memory = os.getenv("DUCKDB_MAX_MEMORY", "4GB")
    threads = os.getenv("DUCKDB_THREADS", "4")
    temp_dir = os.getenv("DUCKDB_TEMP_DIR", str(RAIZ_PROJETO / "data" / "duckdb_temp"))

    temp_path = Path(temp_dir)
    try:
        temp_path.mkdir(parents=True, exist_ok=True)
        # Validação simples de escrita no diretório temporário
        test_file = temp_path / "test_write.tmp"
        test_file.write_text("ok")
        test_file.unlink()
    except Exception as e:
        raise FileNotFoundError(
            f"Diretório temporário DuckDB inválido ou sem permissão de escrita ({temp_path}): {e}"
        ) from e

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not account_id:
        raise ValueError("A variável R2_ACCOUNT_ID não está configurada.")

    if not access_key:
        raise ValueError("A variável R2_ACCESS_KEY_ID não está configurada.")

    if not secret_key:
        raise ValueError("A variável R2_SECRET_ACCESS_KEY não está configurada.")

    endpoint = os.getenv(
        "R2_ENDPOINT",
        f"{account_id}.r2.cloudflarestorage.com",
    )

    endpoint = endpoint.strip().rstrip("/")

    if endpoint.startswith(("https://", "http://")):
        endpoint = urlparse(endpoint).netloc

    if not endpoint:
        raise ValueError("O endpoint do R2 está vazio ou inválido.")

    conn = duckdb.connect(database=":memory:")

    conn.execute("INSTALL httpfs")
    conn.execute("LOAD httpfs")

    # Aplica limites de memória, threads e diretório temporário seguros para grandes volumes (como SP)
    conn.execute(f"SET max_memory='{max_memory}'")
    conn.execute(f"SET threads={threads}")
    temp_dir_sql = str(temp_path).replace("'", "''").replace("\\", "/")
    conn.execute(f"SET temp_directory='{temp_dir_sql}'")

    def definir_configuracao(nome: str, valor: str) -> None:
        valor_sql = valor.replace("'", "''")
        conn.execute(f"SET {nome} = '{valor_sql}'")

    definir_configuracao("s3_endpoint", endpoint)
    definir_configuracao("s3_access_key_id", access_key)
    definir_configuracao("s3_secret_access_key", secret_key)
    definir_configuracao("s3_url_style", "path")
    definir_configuracao("s3_region", "auto")

    return conn


# ============================================================
# VALIDAÇÃO DOS ARQUIVOS PARQUET
# ============================================================


def contar_registros(
    conn: duckdb.DuckDBPyConnection,
    caminho: str | Path,
) -> int:
    """Conta os registros de um arquivo Parquet."""

    caminho_str = str(caminho)

    resultado = conn.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [caminho_str],
    ).fetchone()

    if resultado is None:
        raise RuntimeError(f"Não foi possível obter a contagem de {caminho_str}.")

    return int(resultado[0])


def comparar_arquivos_escalavel(
    conn: duckdb.DuckDBPyConnection,
    caminho_a: str | Path,
    caminho_b: str | Path,
    temp_dir: str | Path | None = None,
) -> bool:
    """
    Compara de forma escalável e segura dois Parquets sem estourar a memória RAM.

    Para evitar OutOfMemoryException em grandes partições (ex: SP com 21M de linhas),
    utiliza GROUP BY com contagem de multiplicidade por registro ou JOIN anti-match.
    O resultado preserva a verificação exata do conteúdo e da multiplicidade de duplicatas.
    """
    arquivo_a = str(caminho_a)
    arquivo_b = str(caminho_b)

    if temp_dir:
        t_path = Path(temp_dir)
        if not t_path.exists():
            raise FileNotFoundError(
                f"Diretório temporário para comparação não existe: {temp_dir}"
            )

    print("  [Etapa Log] Iniciando comparação escalável de arquivos...")

    # 1. Checa contagem simples de registros primeiro
    cnt_a = contar_registros(conn, arquivo_a)
    cnt_b = contar_registros(conn, arquivo_b)

    if cnt_a != cnt_b:
        print(
            f"  [Etapa Log] Divergencia na contagem de registros: A={cnt_a}, B={cnt_b}"
        )
        return False

    # 2. Comparacao exata sem estourar RAM:
    # Agrupa por todas as colunas para contar multiplicidade e compara
    # Forcamos o uso de threads e memoria via parametros se fornecidos
    query_diff = """
    WITH counts_a AS (
        SELECT *, COUNT(*) as __mult
        FROM read_parquet(?)
        GROUP BY ALL
    ),
    counts_b AS (
        SELECT *, COUNT(*) as __mult
        FROM read_parquet(?)
        GROUP BY ALL
    )
    SELECT COUNT(*) FROM (
        (SELECT * FROM counts_a EXCEPT SELECT * FROM counts_b)
        UNION ALL
        (SELECT * FROM counts_b EXCEPT SELECT * FROM counts_a)
    )
    """

    try:
        diferencas = conn.execute(query_diff, [arquivo_a, arquivo_b]).fetchone()
    except Exception as e:
        print(f"  [Etapa Log] Erro na execucao da query de comparacao: {e}")
        raise

    if diferencas is None:
        raise RuntimeError(
            f"Falha na execucao do SQL de comparacao entre {arquivo_a} e {arquivo_b}."
        )

    num_diffs = int(diferencas[0])
    print(
        f"  [Etapa Log] Comparacao escalavel concluida. Total de diferencas de linhas/multiplicidade: {num_diffs}"
    )

    return num_diffs == 0


def comparar_arquivos(
    conn: duckdb.DuckDBPyConnection,
    caminho_a: str | Path,
    caminho_b: str | Path,
) -> bool:
    """Redireciona para a comparação escalável."""
    return comparar_arquivos_escalavel(conn, caminho_a, caminho_b)


# ============================================================
# VERIFICAÇÃO SEGURA DA EXISTÊNCIA NO R2
# ============================================================


def verificar_existencia_remota(destino: str) -> bool:
    """
    Verifica se o objeto existe usando rclone.

    Retorna False somente quando a resposta indica claramente
    ausência do objeto. Erros ambíguos, de autenticação ou rede
    interrompem a operação para evitar uploads indevidos.
    """

    comando = [
        "rclone",
        "lsjson",
        destino,
        "--stat",
    ]

    processo = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    if processo.returncode == 0:
        if not processo.stdout.strip():
            raise RuntimeError(f"O rclone não retornou informações para {destino}.")

        try:
            json.loads(processo.stdout)
        except json.JSONDecodeError as erro:
            raise RuntimeError(
                f"Resposta JSON inválida ao consultar {destino}: "
                f"{processo.stdout[:500]}"
            ) from erro

        return True

    mensagem = (f"{processo.stderr}\n{processo.stdout}").casefold()

    indicadores_de_ausencia = (
        "object not found",
        "no such key",
        "nosuchkey",
        "not found",
        "does not exist",
        "404",
    )

    if any(indicador in mensagem for indicador in indicadores_de_ausencia):
        return False

    raise RuntimeError(
        f"Não foi possível confirmar a existência de {destino}. "
        "A operação foi interrompida por segurança. "
        f"Detalhes: {processo.stderr.strip() or processo.stdout.strip()}"
    )


# ============================================================
# PUBLICAÇÃO E VALIDAÇÃO REMOTA
# ============================================================


def publicar_arquivo(
    conn: duckdb.DuckDBPyConnection,
    origem: Path,
    destino_rclone: str,
    destino_duckdb: str,
) -> int:
    """Publica um Parquet e valida o conteúdo após o envio."""

    print(f"Enviando: {origem}")
    print(f"Destino: {destino_rclone}")

    subprocess.run(
        [
            "rclone",
            "copyto",
            str(origem),
            destino_rclone,
            "--retries",
            "3",
            "--low-level-retries",
            "10",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=7200,
    )

    registros_remotos = contar_registros(
        conn,
        destino_duckdb,
    )

    registros_locais = contar_registros(
        conn,
        origem,
    )

    if registros_remotos != registros_locais:
        raise RuntimeError(
            "A contagem remota diverge da local após o upload: "
            f"local={registros_locais}, remoto={registros_remotos}."
        )

    if not comparar_arquivos(
        conn,
        origem,
        destino_duckdb,
    ):
        raise RuntimeError("A comparação integral falhou após o upload.")

    return registros_remotos


# ============================================================
# PROCESSAMENTO DE CADA UF
# ============================================================


def processar_uf(
    conn: duckdb.DuckDBPyConnection,
    uf: str,
) -> None:
    """Audita e, se necessário, publica a partição de uma UF."""

    original = DIRETORIO_ORIGINAL / f"uf={uf}" / "data_0.parquet"

    reordenado = DIRETORIO_REORDENADO / f"uf={uf}" / "data_0.parquet"

    destino_rclone = f"{REMOTE_ROOT}/uf={uf}/data_0.parquet"

    destino_duckdb = f"s3://{BUCKET}/estabelecimentos/uf={uf}/data_0.parquet"

    registros_reordenado: int | None = None
    registros_remotos: int | None = None
    tamanho_bytes: int | None = None

    try:
        print(f"\n{'=' * 65}")
        print(f"PROCESSANDO UF: {uf}")
        print(f"{'=' * 65}")

        # 1. Validar os arquivos locais.
        print(f"[{uf}] [Etapa 1/5] Validando existência dos arquivos locais...")
        if not original.is_file():
            raise FileNotFoundError(f"Arquivo original não encontrado: {original}")

        if not reordenado.is_file():
            raise FileNotFoundError(f"Arquivo reordenado não encontrado: {reordenado}")

        tamanho_bytes = reordenado.stat().st_size

        if tamanho_bytes <= 0:
            raise ValueError(f"O arquivo reordenado está vazio: {reordenado}")

        # 2. Validar a quantidade de registros.
        print(f"[{uf}] [Etapa 2/5] Contando registros de original e reordenado...")
        registros_originais = contar_registros(
            conn,
            original,
        )

        registros_reordenado = contar_registros(
            conn,
            reordenado,
        )

        if registros_originais != registros_reordenado:
            raise RuntimeError(
                "A quantidade de registros diverge entre "
                f"original ({registros_originais}) e "
                f"reordenado ({registros_reordenado})."
            )

        # 3. Comparar integralmente original e reordenado.
        print(
            f"[{uf}] [Etapa 3/5] Executando comparação integral de dados localmente..."
        )
        if not comparar_arquivos(
            conn,
            original,
            reordenado,
        ):
            raise RuntimeError(
                "O conteúdo do arquivo reordenado diverge do arquivo original."
            )

        print(f"[{uf}] Validação local aprovada: {registros_reordenado:,} registros.")

        # 4. Upload incondicional do arquivo local reordenado validado.
        # Substitui o objeto remoto no Cloudflare R2 com a ordenação física esperada.
        print(f"[{uf}] [Etapa 4/5] Verificando existência remota no R2...")
        existe_remoto = verificar_existencia_remota(
            destino_rclone,
        )

        if existe_remoto:
            try:
                registros_remotos = contar_registros(
                    conn,
                    destino_duckdb,
                )
            except duckdb.Error as erro:
                registros_remotos = None
                print(
                    f"[{uf}] AVISO: não foi possível consultar a quantidade "
                    f"de registros remotos: {type(erro).__name__}: {erro}"
                )

            print(
                f"[{uf}] Objeto remoto já existe "
                f"({registros_remotos if registros_remotos is not None else 'quantidade desconhecida'} registros). "
                "Substituindo pelo Parquet local reordenado..."
            )
        else:
            print(
                f"[{uf}] Objeto remoto ausente. Publicando Parquet local reordenado..."
            )

        # 5. Publicar e validar remotamente.
        print(f"[{uf}] [Etapa 5/5] Iniciando transferência e validação pós-upload...")
        registros_publicados = publicar_arquivo(
            conn=conn,
            origem=reordenado,
            destino_rclone=destino_rclone,
            destino_duckdb=destino_duckdb,
        )

        registrar(
            uf=uf,
            status="PUBLICADA",
            detalhe=(
                "Upload concluído e validado por contagem "
                "e comparação integral do conteúdo."
            ),
            registros=registros_publicados,
            tamanho_bytes=tamanho_bytes,
            remoto_anterior=registros_remotos,
        )

    except (
        duckdb.Error,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        subprocess.SubprocessError,
    ) as erro:
        registrar(
            uf=uf,
            status="FALHA",
            detalhe=(
                f"{type(erro).__name__}: {erro}. "
                "Verifique o estado remoto antes de tentar novamente."
            ),
            registros=locals().get("registros_reordenado"),
            tamanho_bytes=tamanho_bytes,
            remoto_anterior=registros_remotos,
        )


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================


def main() -> int:
    """Executa a auditoria e publicação de todas as UFs ou de UFs específicas via linha de comando."""

    import argparse

    parser = argparse.ArgumentParser(description="Auditoria e publicação de UFs no R2")
    parser.add_argument(
        "--uf",
        type=str,
        default=None,
        help="Executar somente uma UF específica (ex: --uf SP)",
    )
    args = parser.parse_args()

    lista_ufs = [args.uf.upper()] if args.uf else UFS

    conn: duckdb.DuckDBPyConnection | None = None

    try:
        print("=" * 65)
        print("BUSCAFRI — AUDITORIA E PUBLICAÇÃO NO CLOUDFLARE R2")
        print("=" * 65)
        print(f"Bucket: {BUCKET}")
        print(f"Total de UFs: {len(lista_ufs)}")
        print(f"Origem: {DIRETORIO_REORDENADO}")
        print(f"Destino: {REMOTE_ROOT}")

        conn = configurar_duckdb()

        for uf in lista_ufs:
            processar_uf(conn, uf)

    except (
        duckdb.Error,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        subprocess.SubprocessError,
    ) as erro:
        print(
            f"\nERRO FATAL: {type(erro).__name__}: {erro}",
            file=sys.stderr,
        )

        return 1

    finally:
        if conn is not None:
            conn.close()

        try:
            salvar_relatorio()
        except OSError as erro:
            print(
                f"ERRO AO SALVAR O RELATÓRIO: {erro}",
                file=sys.stderr,
            )

    falhas = [item for item in resultados if item["status"] == "FALHA"]

    publicadas = sum(item["status"] == "PUBLICADA" for item in resultados)

    ja_atualizadas = sum(item["status"] == "JA ATUALIZADA" for item in resultados)

    print(f"\n{'=' * 65}")
    print("RESUMO FINAL")
    print(f"{'=' * 65}")
    print(f"UFs previstas: {len(UFS)}")
    print(f"Publicadas e validadas: {publicadas}")
    print(f"Já atualizadas: {ja_atualizadas}")
    print(f"Falhas: {len(falhas)}")

    if falhas:
        print("\nUFs com falha:")

        for item in falhas:
            print(f"  - {item['uf']}: {item['detalhe']}")

        return 1

    if len(resultados) != len(UFS):
        print(
            "\nATENÇÃO: nem todas as UFs foram processadas.",
            file=sys.stderr,
        )
        return 1

    print("\nAuditoria concluída sem falhas registradas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
