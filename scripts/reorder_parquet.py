from pathlib import Path

import duckdb

SORT_COLUMNS = [
    "municipio",
    "cnae_fiscal_principal",
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
]

ROW_GROUP_SIZE = 100_000


def sql_path(path: Path) -> str:
    """Converte um caminho absoluto para um literal de caminho SQL."""
    return path.resolve().as_posix().replace("'", "''")


def sql_literal(path: Path) -> str:
    """Retorna um caminho escapado para uso como literal SQL."""
    return f"'{sql_path(path)}'"


def fetch_count(
    connection: duckdb.DuckDBPyConnection,
    query: str,
) -> int:
    """Executa uma contagem e verifica o resultado."""
    result = connection.execute(query).fetchone()

    if result is None or result[0] is None:
        raise RuntimeError("A consulta não retornou uma contagem válida.")

    count = result[0]

    if not isinstance(count, int):
        raise TypeError(
            f"Esperado um inteiro na contagem; recebido {type(count).__name__}."
        )

    return count


def parquet_schema(
    connection: duckdb.DuckDBPyConnection,
    pattern: str,
) -> list[tuple[str, str]]:
    """Retorna os nomes e tipos das colunas de um conjunto Parquet."""
    result = connection.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{pattern}')"
    ).fetchall()

    return [(str(row[0]), str(row[1])) for row in result]


def get_partitions(directory: Path) -> dict[str, Path]:
    """Identifica as pastas de partição e valida seus nomes."""
    partitions = {
        path.name: path
        for path in directory.iterdir()
        if path.is_dir() and path.name.startswith("uf=")
    }

    for name in partitions:
        uf = name.removeprefix("uf=")
        if not uf or "/" in uf or "\\" in uf:
            raise ValueError(f"Nome de partição inválido: {name}")

    return dict(sorted(partitions.items()))


def reorder_parquet(input_dir: str, output_dir: str) -> bool:
    """Reordena os Parquet locais sem modificar a origem."""
    source = Path(input_dir)
    destination = Path(output_dir)

    if not source.is_dir():
        raise ValueError(f"Diretório de origem não encontrado: {source}")

    if destination.exists():
        raise ValueError(
            f"A pasta de saída já existe: {destination}\n"
            "Nenhum arquivo foi sobrescrito. Valide ou mova a saída "
            "anterior antes de iniciar uma nova execução."
        )

    partitions = get_partitions(source)

    if not partitions:
        raise ValueError(f"Nenhuma partição uf=XX encontrada em {source}")

    for name, partition in partitions.items():
        if not list(partition.glob("*.parquet")):
            raise ValueError(f"Nenhum Parquet encontrado em {name}")

    # Confirma que todas as colunas usadas na ordenação existem.
    with duckdb.connect(database=":memory:") as connection:
        first_partition = next(iter(partitions.values()))
        first_pattern = sql_path(first_partition / "*.parquet")
        columns = parquet_schema(connection, first_pattern)
        column_names = {name for name, _ in columns}

        missing = [column for column in SORT_COLUMNS if column not in column_names]

        if missing:
            raise ValueError(f"Colunas de ordenação ausentes na origem: {missing}")

    # Cria a saída apenas depois das verificações preliminares.
    destination.mkdir(parents=True, exist_ok=False)

    order_by = ", ".join(f'"{column}" ASC NULLS LAST' for column in SORT_COLUMNS)

    try:
        with duckdb.connect(database=":memory:") as connection:
            print("--- REORDENAÇÃO DOS ESTABELECIMENTOS ---")
            print(f"Partições encontradas: {len(partitions)}")

            for index, (partition_name, partition) in enumerate(
                partitions.items(),
                start=1,
            ):
                output_partition = destination / partition_name
                output_partition.mkdir(parents=True, exist_ok=False)

                input_pattern = sql_path(partition / "*.parquet")
                output_file = output_partition / "data_0.parquet"

                query = (
                    "COPY ("
                    "SELECT * "
                    f"FROM read_parquet('{input_pattern}') "
                    f"ORDER BY {order_by}"
                    ") "
                    f"TO {sql_literal(output_file)} "
                    f"(FORMAT PARQUET, ROW_GROUP_SIZE {ROW_GROUP_SIZE})"
                )

                print(f"\n[{index}/{len(partitions)}] Processando {partition_name}...")

                connection.execute(query)

                print(f"Arquivo gerado: {output_file}")

                if not output_file.is_file() or output_file.stat().st_size == 0:
                    raise RuntimeError(
                        f"Arquivo de saída ausente ou vazio: {output_file}"
                    )

        print("\nReordenação concluída.")
        print("A origem não foi modificada.")
        return True

    except (duckdb.Error, OSError, ValueError, RuntimeError, TypeError):
        print(
            "\nERRO: a reordenação foi interrompida. "
            "A pasta de saída pode conter arquivos parciais. "
            "Não a apague automaticamente; inspecione-a primeiro."
        )
        raise


def validate_integrity(
    input_dir: str,
    output_dir: str,
) -> tuple[bool, str]:
    """
    Compara partições, esquema, contagens e conteúdo dos registros.
    Também verifica a ordenação física de cada arquivo de saída.
    """
    source = Path(input_dir)
    destination = Path(output_dir)

    if not source.is_dir() or not destination.is_dir():
        return False, "Diretório de origem ou saída não encontrado."

    try:
        source_partitions = get_partitions(source)
        output_partitions = get_partitions(destination)

        if set(source_partitions) != set(output_partitions):
            missing = sorted(set(source_partitions) - set(output_partitions))
            extra = sorted(set(output_partitions) - set(source_partitions))

            return (
                False,
                (
                    f"Partições divergentes. Ausentes na saída: {missing}; "
                    f"extras na saída: {extra}."
                ),
            )

        total_source = 0
        total_output = 0

        with duckdb.connect(database=":memory:") as connection:
            for partition_name, source_partition in source_partitions.items():
                output_partition = output_partitions[partition_name]

                source_files = sorted(source_partition.glob("*.parquet"))
                output_files = sorted(output_partition.glob("*.parquet"))

                if not source_files or not output_files:
                    return (
                        False,
                        f"Partição sem arquivos Parquet: {partition_name}.",
                    )

                if len(output_files) != 1 or output_files[0].name != "data_0.parquet":
                    return (
                        False,
                        (
                            f"A saída de {partition_name} deve conter "
                            f"exatamente data_0.parquet."
                        ),
                    )

                source_pattern = sql_path(source_partition / "*.parquet")
                output_pattern = sql_path(output_partition / "*.parquet")

                source_schema = parquet_schema(connection, source_pattern)
                output_schema = parquet_schema(connection, output_pattern)

                if source_schema != output_schema:
                    return (
                        False,
                        (
                            f"Esquema diferente na partição {partition_name}. "
                            f"Origem: {source_schema}; saída: {output_schema}."
                        ),
                    )

                source_count = fetch_count(
                    connection,
                    f"SELECT COUNT(*) FROM read_parquet('{source_pattern}')",
                )
                output_count = fetch_count(
                    connection,
                    f"SELECT COUNT(*) FROM read_parquet('{output_pattern}')",
                )

                if source_count != output_count:
                    return (
                        False,
                        (
                            f"Contagem divergente em {partition_name}: "
                            f"origem={source_count:,}; saída={output_count:,}."
                        ),
                    )

                total_source += source_count
                total_output += output_count

                # Compara as linhas como multiconjuntos, preservando
                # a multiplicidade de registros duplicados.
                # As duas direções detectam perdas e registros extras.
                differences_query = (
                    "SELECT COUNT(*) FROM ("
                    "("
                    "SELECT * "
                    f"FROM read_parquet('{source_pattern}') "
                    "EXCEPT ALL "
                    f"SELECT * FROM read_parquet('{output_pattern}')"
                    ") UNION ALL ("
                    "SELECT * "
                    f"FROM read_parquet('{output_pattern}') "
                    "EXCEPT ALL "
                    f"SELECT * FROM read_parquet('{source_pattern}')"
                    ")"
                    ") AS differences"
                )

                differences = fetch_count(connection, differences_query)

                if differences:
                    return (
                        False,
                        (
                            f"Conteúdo diferente na partição {partition_name}: "
                            f"{differences:,} diferenças encontradas."
                        ),
                    )

                # Compara a posição física de cada linha com a posição
                # que ela teria na ordenação solicitada. O número da
                # linha desempata chaves iguais e evita ambiguidades.
                order_columns = ", ".join(
                    f'"{column}" ASC NULLS LAST' for column in SORT_COLUMNS
                )

                ordering_query = (
                    "SELECT COUNT(*) FROM ("
                    "SELECT "
                    "ROW_NUMBER() OVER (ORDER BY file_row_number) AS actual_pos, "
                    f"ROW_NUMBER() OVER (ORDER BY {order_columns}, "
                    "file_row_number) AS expected_pos "
                    f"FROM read_parquet('{output_pattern}', "
                    "file_row_number = true)"
                    ") AS positions "
                    "WHERE actual_pos <> expected_pos"
                )

                ordering_errors = fetch_count(connection, ordering_query)

                if ordering_errors:
                    return (
                        False,
                        (
                            f"Ordenação inválida em {partition_name}: "
                            f"{ordering_errors:,} posições divergentes."
                        ),
                    )

                print(
                    f"{partition_name}: OK | "
                    f"{output_count:,} registros | "
                    "esquema, conteúdo e ordenação validados"
                )

        if total_source != total_output:
            return (
                False,
                (
                    f"Contagem total divergente: origem={total_source:,}; "
                    f"saída={total_output:,}."
                ),
            )

        return (
            True,
            (
                f"Validação completa aprovada: partições, esquema, contagens, "
                f"conteúdo e ordenação conferidos. "
                f"Total: {total_output:,} registros."
            ),
        )

    except (duckdb.Error, OSError, ValueError, RuntimeError, TypeError) as error:
        return False, f"Erro durante a validação: {error}"


if __name__ == "__main__":
    input_directory = "data/particionado/estabelecimentos"
    output_directory = "data/reordenado/estabelecimentos"

    try:
        if reorder_parquet(input_directory, output_directory):
            valid, message = validate_integrity(
                input_directory,
                output_directory,
            )

            print(f"\n{'SUCESSO' if valid else 'FALHA'}: {message}")

            if not valid:
                raise RuntimeError(
                    "A validação falhou. Não publique os arquivos no R2."
                )

    except (duckdb.Error, OSError, ValueError, RuntimeError, TypeError) as error:
        print(f"\nERRO: {error}")
        raise SystemExit(1) from error
