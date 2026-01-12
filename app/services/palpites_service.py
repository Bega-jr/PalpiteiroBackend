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
    # nível 0 = regras completas
    # nível 1 = regras relaxadas
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
# GERADOR PRINCIPAL
# ==========================

def gerar_palpites_validos(qtd_palpites=7):
    try:
        supabase = get_supabase()
        data_ref = date.today().isoformat()

        # 🔒 evita duplicidade diária
        if _ja_existe_para_data(data_ref):
            return {
                "status": "ignorado",
                "motivo": "palpites já existem para a data",
                "data": data_ref
            }

        estatisticas = _buscar_estatisticas()
        if not estatisticas:
            raise Exception("Estatísticas não encontradas")

        # 🎯 monta pool probabilístico
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

        palpites_gerados = []

        for indice in range(qtd_palpites):
            tentativas = 0
            nivel = 0
            filtros_aplicados = ["soma", "pares", "sequencias", "probabilidade"]

            while tentativas < 300:
                numeros = sorted(
                    random.choices(
                        [n for n, _ in pool],
                        weights=[p for _, p in pool],
                        k=15
                    )
                )

                numeros = sorted(set(numeros))
                if len(numeros) != 15:
                    tentativas += 1
                    continue

                metricas = _calcular_metricas(numeros)

                if not _palpite_valido(metricas, nivel):
                    tentativas += 1
                    if tentativas == 150:
                        nivel = 1
                        filtros_aplicados.append("fallback_relaxado")
                    continue

                pesos_map = {n: p for n, p in pool}
                score_medio = round(
                    sum(pesos_map[n] for n in numeros) / 15, 4
                )

                registro = {
                    "data_referencia": data_ref,
                    "indice_palpite": indice,
                    "numeros": json.dumps(numeros),
                    "soma_total": metricas["soma_total"],
                    "pares": metricas["pares"],
                    "impares": metricas["impares"],
                    "qtd_sequencias": metricas["qtd_sequencias"],
                    "metricas": json.dumps({
                        "score_medio": score_medio,
                        "nivel_regra": nivel,
                        "metodo": "probabilistico_v2"
                    }),
                    "filtros_aplicados": json.dumps(filtros_aplicados),
                    "tipo": "fixo" if indice == 0 else "estatistico",
                    "origem": "sistema"
                }

                supabase.table("palpites_validos").insert(registro).execute()
                palpites_gerados.append(registro)
                break

        return {
            "status": "ok",
            "gerados": len(palpites_gerados),
            "data": data_ref
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

