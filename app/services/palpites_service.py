from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import random
import json
import traceback
from datetime import date

# ==========================
# UTILIDADES
# ==========================

def _calcular_metricas(numeros):
    pares = sum(1 for n in numeros if n % 2 == 0)
    impares = 15 - pares
    soma = sum(numeros)

    sequencias = 0
    seq_atual = 1
    for i in range(1, len(numeros)):
        if numeros[i] == numeros[i - 1] + 1:
            seq_atual += 1
            sequencias = max(sequencias, seq_atual)
        else:
            seq_atual = 1

    return {
        "soma_total": soma,
        "pares": pares,
        "impares": impares,
        "qtd_sequencias": sequencias
    }


def _palpite_valido(metricas):
    if not (170 <= metricas["soma_total"] <= 210):
        return False
    if not (6 <= metricas["pares"] <= 9):
        return False
    if metricas["qtd_sequencias"] > 4:
        return False
    return True


# ==========================
# ESTATÍSTICAS
# ==========================

def _buscar_estatisticas():
    supabase = get_supabase()
    res = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, score, atraso, tendencia")
        .execute()
    )
    return res.data or []


# ==========================
# GERADOR EM MEMÓRIA (BACKTEST)
# ==========================

def gerar_palpites_em_memoria(qtd_palpites=7):
    estatisticas = _buscar_estatisticas()

    if not estatisticas:
        raise Exception("Estatísticas não encontradas")

    pool = []
    for e in estatisticas:
        score = float(e.get("score") or 0)
        atraso = int(e.get("atraso") or 0)
        tendencia = float(e.get("tendencia") or 0)

        peso = (
            score * 0.5 +
            (1 / (atraso + 1)) * 0.3 +
            tendencia * 0.2
        )

        pool.append((e["numero"], peso))

    palpites = []

    for _ in range(qtd_palpites):
        tentativas = 0

        while tentativas < 200:
            numeros = sorted(
                set(
                    random.choices(
                        [n for n, _ in pool],
                        weights=[p for _, p in pool],
                        k=15
                    )
                )
            )

            if len(numeros) != 15:
                tentativas += 1
                continue

            metricas = _calcular_metricas(numeros)

            if not _palpite_valido(metricas):
                tentativas += 1
                continue

            palpites.append(numeros)
            break

    return palpites


# ==========================
# GERADOR COM PERSISTÊNCIA (PRODUÇÃO)
# ==========================

def gerar_palpites_validos(qtd_palpites=7):
    try:
        supabase = get_supabase()
        estatisticas = _buscar_estatisticas()

        if not estatisticas:
            raise Exception("Estatísticas não encontradas")

        pool = []
        for e in estatisticas:
            score = float(e.get("score") or 0)
            atraso = int(e.get("atraso") or 0)
            tendencia = float(e.get("tendencia") or 0)

            peso = (
                score * 0.5 +
                (1 / (atraso + 1)) * 0.3 +
                tendencia * 0.2
            )

            pool.append((e["numero"], peso))

        data_ref = date.today().isoformat()
        gerados = 0

        for indice in range(qtd_palpites):
            tentativas = 0

            while tentativas < 200:
                numeros = sorted(
                    set(
                        random.choices(
                            [n for n, _ in pool],
                            weights=[p for _, p in pool],
                            k=15
                        )
                    )
                )

                if len(numeros) != 15:
                    tentativas += 1
                    continue

                metricas = _calcular_metricas(numeros)

                if not _palpite_valido(metricas):
                    tentativas += 1
                    continue

                registro = {
                    "data_referencia": data_ref,
                    "indice_palpite": indice,
                    "numeros": json.dumps(numeros),
                    "soma_total": metricas["soma_total"],
                    "pares": metricas["pares"],
                    "impares": metricas["impares"],
                    "qtd_sequencias": metricas["qtd_sequencias"],
                    "metricas": json.dumps({
                        "metodo": "probabilistico_v1"
                    }),
                    "filtros_aplicados": json.dumps([
                        "soma", "pares", "sequencias", "probabilidade"
                    ]),
                    "tipo": "estatistico" if indice > 0 else "fixo",
                    "origem": "sistema"
                }

                supabase.table("palpites_validos").insert(registro).execute()
                gerados += 1
                break

        return {"status": "ok", "gerados": gerados}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

