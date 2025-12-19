from pathlib import Path
import unicodedata

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def normalizar_nome(nome: str) -> str:
    return unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode("utf-8").lower()


def localizar_arquivo_lotofacil():
    if not DATA_DIR.exists():
        raise FileNotFoundError("Diretório data/ não encontrado")

    for arquivo in DATA_DIR.iterdir():
        if arquivo.suffix.lower() == ".xlsx":
            nome_normalizado = normalizar_nome(arquivo.name)
            if "lotofacil" in nome_normalizado:
                return arquivo

    raise FileNotFoundError(
        "Arquivo Lotofácil.xlsx não encontrado em data/"
    )


LOTOFACIL_FILE = localizar_arquivo_lotofacil()
