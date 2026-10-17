import time
from pathlib import Path

from scripts.reorder_parquet import reorder_parquet, validate_integrity


def test_single_uf():
    # Test execution for uf=AC to check speed and validation logic
    input_dir = "data/particionado/estabelecimentos"
    temp_input = Path("temp_test_input")
    temp_output = Path("temp_test_output")

    if temp_input.exists():
        import shutil

        shutil.rmtree(temp_input)
    if temp_output.exists():
        import shutil

        shutil.rmtree(temp_output)

    # Copy only uf=AC folder structure
    (temp_input / "uf=AC").mkdir(parents=True)
    import shutil

    shutil.copy(
        Path(input_dir) / "uf=AC" / "data_0.parquet",
        temp_input / "uf=AC" / "data_0.parquet",
    )

    start = time.time()
    print("Iniciando teste com uf=AC...")
    reorder_parquet(str(temp_input), str(temp_output))
    valid, msg = validate_integrity(str(temp_input), str(temp_output))
    print(f"Resultado: {valid} - {msg}")
    print(f"Tempo decorrido: {time.time() - start:.2f}s")

    # Clean up
    shutil.rmtree(temp_input)
    shutil.rmtree(temp_output)


if __name__ == "__main__":
    test_single_uf()
