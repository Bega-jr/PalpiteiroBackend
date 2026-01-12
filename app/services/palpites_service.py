from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import random
import json
import traceback
from datetime import date
from typing import Any


# ==========================
# UTILIDADES
# ==========================

def safe_float(valor: Any, default: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _calcular_metricas(numeros):
    pares = sum(1 for n in numeros if n % 2 == 0)
    impares = 15 - pares
    soma = sum(numeros)

    sequencias = 1
    max_seq = 1
    for i in range(1, len(numeros)):
        if numeros[i] == numeros[i - 1] + 1:
            sequencias += 1
            max_seq = max(max_seq, sequencias)
        else:
            sequencias = 1

    return {
        "soma_total": soma,
        "pares": pares,
        "impares": impares,
        "qtd_sequencias": max_seq
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
# BUSCA ESTATÍSTICAS
# ==========================

def _buscar_estatisticas():
    supabase = get_supabase()
    res = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, score, frequencia, atraso, tendencia")
        .execute()
    )
    return res.data or []


# ==========================
# GERADOR PRINCIPAL
# ==========================

def gerar_palpites_validos(qtd_palpites: int = 7):
    try:
        supabase = get_supabase()
        estatisticas = _buscar_estatisticas()

        if not estatisticas:
            raise Exception("Estatísticas não encontradas")

        # ==========================
        # NORMALIZAÇÃO DE PESOS
        # ==========================

        pool = []
        for e in estatisticas:
            score = safe_float(e.get("score"))
            atraso = safe_float(e.get("atraso"))
            tendencia = safe_float(e.get("tendencia"))

            peso = (
                score * 0.5 +
                (1 / (atraso + 1)) * 0.3 +
                tendencia * 0.2
            )

            pool.append((e["numero"], max(peso, 0.0001)))

        numeros_pool = [n for n, _ in pool]
        pesos_pool = [p for _, p in pool]

        data_ref = date.today().isoformat()
        palpites_gerados = []

        # ==========================
        # GERAÇÃO DOS PALPITES
        # ==========================

        for indice in range(qtd_palpites):
            tentativas = 0

            while tentativas < 300:
                numeros = sorted(
                    set(
                        random.choices(
                            numeros_pool,
                            weights=pesos_pool,
                            k=20
                        )
                    )
                )

                if len(numeros) < 15:
                    tentativas += 1
                    continue

                numeros = numeros[:15]
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
                        "metodo": "probabilistico_v2",
                        "peso_medio": round(sum(pesos_pool) / len(pesos_pool), 4)
                    }),
                    "filtros_aplicados": json.dumps([
                        "soma",
                        "pares",
                        "sequencias",
                        "peso_dinamico"
                    ]),
                    "tipo": "fixo" if indice == 0 else "estatistico",
                    "origem": "sistema"
                }

                supabase.table("palpites_validos").insert(registro).execute()
                palpites_gerados.append(registro)
                break

        return {
            "status": "ok",
            "gerados": len(palpites_gerados)
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
