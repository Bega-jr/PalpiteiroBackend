import requests
import csv
import os

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "data/Lotofacil.csv"

COLUNAS_POSSIVEIS_CONCURSO = [
    "concurso",
    "Concurso",
    "numero",
    "NUM_CONCURSO"
]

def buscar_dados():
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return response.json()

def garantir_diretorio():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

def detectar_coluna_concurso(fieldnames):
    for col in COLUNAS_POSSIVEIS_CONCURSO:
        if col in fieldnames:
            return col
    return None

def ler_ultimo_concurso():
    if not os.path.exists(CSV_PATH):
        return 0

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        coluna = detectar_coluna_concurso(reader.fieldnames)
        if not coluna:
            raise Exception(
                f"❌ Coluna de concurso não encontrada no CSV. "
                f"Colunas atuais: {reader.fieldnames}"
            )

        concursos = [int(row[coluna]) for row in reader if row[coluna].isdigit()]

    return max(concursos) if concursos else 0

def salvar_concurso(dados):
    garantir_diretorio()

    existe = os.path.exists(CSV_PATH)

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not existe:
            writer.writerow([
                "concurso",
                "data",
                "numeros",
                "arrecadacao_total",
                "ganhadores_15"
            ])

        writer.writerow([
            dados["numero"],
            dados["dataApuracao"],
            ",".join(dados["listaDezenas"]),
            dados["valorArrecadado"],
            dados["quantidadeGanhadores"]
        ])

def main():
    dados = buscar_dados()
    ultimo_csv = ler_ultimo_concurso()

    concurso_api = int(dados["numero"])

    if concurso_api > ultimo_csv:
        salvar_concurso(dados)
        print(f"✅ Concurso {concurso_api} salvo no CSV")
    else:
        print(f"ℹ️ CSV já atualizado (último: {ultimo_csv})")

if __name__ == "__main__":
    main()
