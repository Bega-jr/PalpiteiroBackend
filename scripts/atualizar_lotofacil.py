import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "lotofacil_resultados.csv"


CAMPOS = [
    "loteria", "concurso", "data",
    *[f"bola{i}" for i in range(1, 16)],
    "arrecadacao", "acumulado", "estimativa_proximo",
    "ganhadores_15", "valor_15",
    "ganhadores_14", "valor_14",
    "ganhadores_13", "valor_13",
    "ganhadores_12", "valor_12",
    "ganhadores_11", "valor_11",
]


def carregar_csv():
    if CSV_PATH.exists():
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame(columns=CAMPOS)


def ultimo_concurso(df):
    if df.empty:
        return 0
    return int(df["concurso"].max())


def buscar_concurso(numero=None):
    url = BASE_URL if numero is None else f"{BASE_URL}/{numero}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extrair_rateio(lista, faixa):
    for r in lista:
        if r["faixa"] == faixa:
            return r["numeroDeGanhadores"], r["valorPremio"]
    return 0, 0.0


def normalizar(dados):
    g15, v15 = extrair_rateio(dados["listaRateioPremio"], 1)
    g14, v14 = extrair_rateio(dados["listaRateioPremio"], 2)
    g13, v13 = extrair_rateio(dados["listaRateioPremio"], 3)
    g12, v12 = extrair_rateio(dados["listaRateioPremio"], 4)
    g11, v11 = extrair_rateio(dados["listaRateioPremio"], 5)

    registro = {
        "loteria": "lotofacil",
        "concurso": int(dados["numero"]),
        "data": datetime.strptime(
            dados["dataApuracao"], "%d/%m/%Y"
        ).strftime("%Y-%m-%d"),
        "arrecadacao": dados["valorArrecadado"],
        "acumulado": dados["acumulado"],
        "estimativa_proximo": dados["valorEstimadoProximoConcurso"],
        "ganhadores_15": g15,
        "valor_15": v15,
        "ganhadores_14": g14,
        "valor_14": v14,
        "ganhadores_13": g13,
        "valor_13": v13,
        "ganhadores_12": g12,
        "valor_12": v12,
        "ganhadores_11": g11,
        "valor_11": v11,
    }

    dezenas = sorted(int(d) for d in dados["listaDezenas"])
    for i, d in enumerate(dezenas, start=1):
        registro[f"bola{i}"] = d

    return registro


def main():
    df = carregar_csv()
    ultimo_salvo = ultimo_concurso(df)

    print(f"📌 Último concurso salvo: {ultimo_salvo}")

    ultimo_api = int(buscar_concurso()["numero"])
    print(f"🌐 Último concurso na API: {ultimo_api}")

    novos = []

    for concurso in range(ultimo_salvo + 1, ultimo_api + 1):
        print(f"⬇️ Buscando concurso {concurso}")
        dados = buscar_concurso(concurso)
        novos.append(normalizar(dados))

    if not novos:
        print("✅ Nenhum concurso novo.")
        return

    df_novos = pd.DataFrame(novos)
    df_final = pd.concat([df, df_novos], ignore_index=True)
    df_final.sort_values("concurso", inplace=True)

    df_final.to_csv(CSV_PATH, index=False)
    print(f"✅ {len(novos)} concursos adicionados com sucesso.")


if __name__ == "__main__":
    main()

