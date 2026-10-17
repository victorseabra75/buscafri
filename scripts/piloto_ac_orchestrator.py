import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

# Configurações do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UF_PILOTO = "uf=AC"

LOCAL_ORIGINAL = (
    PROJECT_ROOT
    / "data"
    / "particionado"
    / "estabelecimentos"
    / UF_PILOTO
    / "data_0.parquet"
)

LOCAL_REORDENADO = (
    PROJECT_ROOT
    / "data"
    / "reordenado"
    / "estabelecimentos"
    / UF_PILOTO
    / "data_0.parquet"
)

REMOTE_BUCKET = "r2:buscafri-data/estabelecimentos"
REMOTE_OBJECT = f"{REMOTE_BUCKET}/{UF_PILOTO}/data_0.parquet"
REMOTE_S3_URI = f"s3://buscafri-data/estabelecimentos/{UF_PILOTO}/data_0.parquet"

EXPECTED_SIZE = 12_107_118

OPERATIONAL_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    IndexError,
    subprocess.SubprocessError,
)


def load_validate_integrity() -> Callable[[str, str], bool]:
    """Carrega a função de validação pelo caminho absoluto."""
    validator_path = PROJECT_ROOT / "scripts" / "validar_reordenacao_r2.py"

    if not validator_path.is_file():
        raise FileNotFoundError(
            f"Arquivo de validação não encontrado: {validator_path}"
        )

    spec = importlib.util.spec_from_file_location(
        "validar_reordenacao_r2",
        validator_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar o módulo: {validator_path}")

    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    validator = getattr(module, "validate_integrity", None)

    if not callable(validator):
        raise TypeError(
            "A função validate_integrity não foi encontrada "
            "ou não é chamável em validar_reordenacao_r2.py."
        )

    return cast(Callable[[str, str], bool], validator)


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Executa um comando externo e informa falhas."""
    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        print(f"Erro no comando {' '.join(cmd)}: {error.stderr}")
        raise
    except FileNotFoundError:
        print(f"Executável não encontrado: {cmd[0]}")
        raise


def get_remote_info() -> tuple[int | None, str]:
    """Retorna o tamanho e o status do objeto remoto."""
    try:
        result = run_cmd(["rclone", "lsjson", REMOTE_OBJECT])
        objects = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Resposta JSON inválida do rclone.") from error
    except subprocess.CalledProcessError:
        return None, "ERRO_ACESSO"

    if not isinstance(objects, list):
        raise TypeError("Formato inesperado na resposta do rclone.")

    for obj in objects:
        if not isinstance(obj, dict):
            raise TypeError("Objeto inválido na resposta do rclone.")

        if obj.get("Path") == "data_0.parquet" and not obj.get("IsDir", False):
            size = obj.get("Size")

            if not isinstance(size, int):
                raise TypeError("Tamanho remoto inválido.")

            return size, "OK"

    return None, "AUSENTE"


def verify_preconditions(
    validate_integrity: Callable[[str, str], bool],
) -> str:
    """Verifica os arquivos locais e o objeto remoto (incluindo integridade pré-substituição)."""
    print("--- VERIFICANDO PRÉ-CONDIÇÕES ---")

    for local_file in (LOCAL_ORIGINAL, LOCAL_REORDENADO):
        if not local_file.is_file():
            raise FileNotFoundError(f"Arquivo local ausente: {local_file}")

    size, status = get_remote_info()

    if status == "ERRO_ACESSO":
        raise RuntimeError("Falha de acesso ao R2. Operação interrompida.")
    if status == "AUSENTE":
        print("Objeto remoto ausente. Recuperação de emergência necessária.")
        return "AUSENTE"

    if size != EXPECTED_SIZE:
        raise RuntimeError(f"Tamanho remoto inesperado: {size} bytes.")

    # Nova verificação: validar a integridade do objeto remoto atual contra o original local
    print("Validando integridade do objeto remoto atual contra o original local...")
    try:
        if not validate_integrity(str(LOCAL_ORIGINAL), REMOTE_S3_URI):
            raise RuntimeError(
                "A validação de integridade do objeto remoto atual falhou. "
                "Operação abortada antes de enviar o arquivo reorganizado."
            )
    except OPERATIONAL_ERRORS as error:
        raise RuntimeError(
            f"Erro durante a validação de integridade do objeto remoto: {error}"
        ) from error

    print("Pré-condições validadas com sucesso.")
    return "OK"


def handle_emergency_recovery(
    validate_integrity: Callable[[str, str], bool],
) -> int:
    """Pede confirmação antes de restaurar o original local."""
    print("--- MODO DE RECUPERAÇÃO DE EMERGÊNCIA ---")

    confirm = (
        input("Confirmar restauração do arquivo original no R2? [s/N]: ")
        .strip()
        .lower()
    )

    if confirm != "s":
        print("Recuperação cancelada pelo usuário.")
        return 1

    try:
        run_cmd(
            [
                "rclone",
                "copyto",
                str(LOCAL_ORIGINAL),
                REMOTE_OBJECT,
            ]
        )

        if validate_integrity(str(LOCAL_ORIGINAL), REMOTE_S3_URI):
            print("Recuperação concluída e validada.")
            return 0

        print("CRÍTICO: restauração não passou na validação.")
        return 1

    except OPERATIONAL_ERRORS as error:
        print(f"CRÍTICO: falha na recuperação: {error}")
        return 1


def perform_rollback(
    validate_integrity: Callable[[str, str], bool],
) -> bool:
    """Restaura o original e valida o resultado."""
    print("--- INICIANDO ROLLBACK ---")

    try:
        run_cmd(
            [
                "rclone",
                "copyto",
                str(LOCAL_ORIGINAL),
                REMOTE_OBJECT,
            ]
        )

        if validate_integrity(str(LOCAL_ORIGINAL), REMOTE_S3_URI):
            print("Rollback validado com sucesso.")
            return True

        print("CRÍTICO: rollback não passou na validação.")
        return False

    except OPERATIONAL_ERRORS as error:
        print(f"CRÍTICO: falha no rollback: {error}")
        return False


def main() -> int:
    try:
        validate_integrity = load_validate_integrity()
        status = verify_preconditions(validate_integrity)
    except OPERATIONAL_ERRORS as error:
        print(f"Erro nas pré-condições: {error}")
        return 1

    if status == "AUSENTE":
        return handle_emergency_recovery(validate_integrity)

    print(f"--- SUBSTITUIÇÃO PILOTO {UF_PILOTO} ---")

    try:
        run_cmd(
            [
                "rclone",
                "copyto",
                str(LOCAL_REORDENADO),
                REMOTE_OBJECT,
            ]
        )

        # Usar try/finally ou garantir que exceções inesperadas disparem rollback
        validation_passed = False
        try:
            validation_passed = validate_integrity(str(LOCAL_REORDENADO), REMOTE_S3_URI)
        except OPERATIONAL_ERRORS as val_error:
            print(f"Exceção capturada durante a validação pós-upload: {val_error}")
            validation_passed = False

        if not validation_passed:
            raise RuntimeError("Validação pós-upload falhou ou levantou erro.")

        print("PILOTO CONCLUÍDO COM SUCESSO.")
        return 0

    except OPERATIONAL_ERRORS as error:
        print(f"ERRO: a substituição falhou: {error}")

        if perform_rollback(validate_integrity):
            print("Arquivo original restaurado.")
        else:
            print(
                "CRÍTICO: falha na recuperação. "
                "Verifique o objeto remoto e restaure o backup manualmente."
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
