import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CAIXA_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

def calcular_pares_impares(dezenas):
    pares = sum(1 for d in dezenas if d % 2 == 0)
    impares = len(dezenas) - pares
    return pares, impares, sum(dezenas)

def buscar_dados_caixa():
    headers = {"Accept": "application/json"}
    r = requests.get(CAIXA_URL, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def formatar_registro(dados):
    dezenas = list(map(int, dados["listaDezenas"]))

    pares, impares, soma = calcular_pares_impares(dezenas)

    rateio = {r["descricaoFaixa"]: r for r in dados["listaRateio"]}

    return {
        "concurso": dados["numero"],
        "data": dados["dataApuracao"],

        "dezenas": dezenas,
        "soma": soma,
        "pares": pares,
        "impares": impares,

        "arrecadacao": dados.get("valorArrecadado"),
        "acumulado": dados.get("acumulado"),

        "ganhadores_15": rateio["15 acertos"]["numeroGanhadores"],
        "valor_15": rateio["15 acertos"]["valorPremio"],

        "ganhadores_14": rateio["14 acertos"]["numeroGanhadores"],
        "valor_14": rateio["14 acertos"]["valorPremio"],

        "ganhadores_13": rateio["13 acertos"]["numeroGanhadores"],
        "valor_13": rateio["13 acertos"]["valorPremio"],

        "ganhadores_12": rateio["12 acertos"]["numeroGanhadores"],
        "valor_12": rateio["12 acertos"]["valorPremio"],

        "ganhadores_11": rateio["11 acertos"]["numeroGanhadores"],
        "valor_11": rateio["11 acertos"]["valorPremio"],

        "estimativa_proximo": dados.get("valorEstimadoProximoConcurso"),

        "municipios": dados.get("listaMunicipioUFGanhadores", [])
    }

def upsert_concurso(registro):
    supabase.table("lotofacil_concursos").upsert(
        registro,
        on_conflict="concurso"
    ).execute()

def main():
    dados = buscar_dados_caixa()
    registro = formatar_registro(dados)
    upsert_concurso(registro)
    print(f"Concurso {registro['concurso']} salvo com sucesso")

if __name__ == "__main__":
    main()
