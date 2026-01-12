from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import random
import json
import traceback
from datetime import date


# ==========================
# UTILIDADES
# ==========================

def safe_float(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


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


def _palpite_valido(metricas, nivel=0):
    if nivel == 0:
        if not (170 <= metricas["soma_total"] <= 210):
            return False
        if not (6 <= metricas["pares"] <= 9):
            return False
        if metricas["qtd_sequencias"] > 4:
            return False
    else:
        if not (165 <= metricas["soma_total"] <= 215):
            return False
        if not (5 <= metricas["pares"] <= 10):
            return False
        if metricas["qtd_sequencias"] > 5:
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


def _ja_existe_para_data(data_ref):
    supabase = get_supabase()
    res = (
        supabase
        .table("palpites_validos")
        .select("id")
        .eq("data_referencia", data_ref)
        .limit(1)
        .execute()
    )
    return bool(res.data)


# ==========================
# CORE REUTILIZÁVEL
# ==========================

def _gerar_palpites_core(
    estatisticas,
    qtd_palpites=7,
    persistir=False,
    data_ref=None
):
    if not data_ref:
        data_ref = date.today().isoformat()

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

        pool.append((int(e["numero"]), max(peso, 0.01)))

    palpites = []

    for indice in range(qtd_palpites):
        tentativas = 0
        nivel = 0

        while tentativas < 300:
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

            if not _palpite_valido(metricas, nivel):
                tentativas += 1
                if tentativas == 150:
                    nivel = 1
                continue

            if persistir:
                supabase = get_supabase()
                supabase.table("palpites_validos").insert({
                    "data_referencia": data_ref,
                    "indice_palpite": indice,
                    "numeros": json.dumps(numeros),
                    "soma_total": metricas["soma_total"],
                    "pares": metricas["pares"],
                    "impares": metricas["impares"],
                    "qtd_sequencias": metricas["qtd_sequencias"],
                    "metricas": json.dumps({
                        "nivel_regra": nivel,
                        "metodo": "probabilistico_v2"
                    }),
                    "filtros_aplicados": json.dumps([
                        "soma", "pares", "sequencias", "probabilidade"
                    ]),
                    "tipo": "fixo" if indice == 0 else "estatistico",
                    "origem": "sistema"
                }).execute()

            palpites.append(numeros)
            break

    return palpites


# ==========================
# API PÚBLICA
# ==========================

def gerar_palpites_validos(qtd_palpites=7):
    try:
        data_ref = date.today().isoformat()

        if _ja_existe_para_data(data_ref):
            return {
                "status": "ignorado",
                "data": data_ref
            }

        estatisticas = _buscar_estatisticas()
        if not estatisticas:
            raise Exception("Estatísticas não encontradas")

        _gerar_palpites_core(
            estatisticas=estatisticas,
            qtd_palpites=qtd_palpites,
            persistir=True,
            data_ref=data_ref
        )

        return {
            "status": "ok",
            "gerados": qtd_palpites,
            "data": data_ref
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


