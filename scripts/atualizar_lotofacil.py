import requests
import csv
import os

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "data/Lotofacil.csv"

def buscar_dados():
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return response.json()

def garantir_diretorio():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

def ler_ultimo_concurso():
    if not os.path.exists(CSV_PATH):
        return 0

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=';')
        next(reader, None)

        concursos = []
        for row in reader:
            if row and row[0].isdigit():
                concursos.append(int(row[0]))

    return max(concursos) if concursos else 0

def obter_ganhadores_15(dados):
    for faixa in dados.get("listaRateioPremio", []):
        if "15" in faixa.get("descricaoFaixa", ""):
            return faixa.get("numeroDeGanhadores", 0)
    return 0

def salvar_concurso(dados):
    garantir_diretorio()
    existe = os.path.exists(CSV_PATH)

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=';')

        if not existe:
            writer.writerow([
                "Concurso",
                "Data Sorteio",
                "Numeros",
                "Arrecadacao Total",
                "Ganhadores 15"
            ])

        writer.writerow([
            dados.get("numero"),
            dados.get("dataApuracao"),
            ",".join(dados.get("listaDezenas", [])),
            dados.get("valorArrecadado", 0),
            obter_ganhadores_15(dados)
        ])

def main():
    dados = buscar_dados()

    ultimo_csv = ler_ultimo_concurso()
    concurso_api = int(dados.get("numero", 0))

    if concurso_api > ultimo_csv:
        salvar_concurso(dados)
        print(f"✅ Concurso {concurso_api} adicionado ao CSV")
    else:
        print(f"ℹ️ CSV já atualizado (último concurso: {ultimo_csv})")

if __name__ == "__main__":
    main()
