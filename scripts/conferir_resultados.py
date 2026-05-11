import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


# ======================================================
# CONFIG
# ======================================================

PESO_ACERTOS = {
    11: 1,
    12: 2,
    13: 5,
    14: 10,
    15: 15
}

NUMEROS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}


# ======================================================
# HELPERS
# ======================================================

def parse_numeros(valor):
    if not valor:
        return None

    try:
        if isinstance(valor, list):
            return [int(x) for x in valor]

        parsed = json.loads(valor)

        if isinstance(parsed, list):
            return [int(x) for x in parsed]

        if isinstance(parsed, str):
            parsed2 = json.loads(parsed)
            return [int(x) for x in parsed2]

        return None

    except Exception as e:
        print(f"⚠️ Erro parseando números: {valor} -> {e}")
        return None


def extrair_estrutura(nums):

    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]

    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in NUMEROS_PRIMOS),
        "linhas": linhas,
        "hash_estrutura": "-".join(map(str, linhas))
    }


def gerar_chave_memoria(est):
    return (
        est["soma_faixa"],
        est["pares"],
        est["primos"],
        est["hash_estrutura"]
    )


# ======================================================
# MEMÓRIA
# ======================================================

def carregar_memoria(supabase):

    print("🧠 Carregando memória em cache...")

    memoria = {}

    res = supabase.table("memoria_cenarios") \
        .select("*") \
        .execute()

    for item in (res.data or []):

        chave = (
            item["soma_faixa"],
            item["pares"],
            item["primos"],
            item.get("hash_estrutura", "")
        )

        memoria[chave] = item

    print(f"✅ {len(memoria)} cenários carregados")

    return memoria


def atualizar_memoria_local(memoria_cache, nums, acertos):

    est = extrair_estrutura(nums)

    chave = gerar_chave_memoria(est)

    peso = PESO_ACERTOS.get(acertos, 0)

    if chave not in memoria_cache:

        memoria_cache[chave] = {
            "id": None,

            "soma_faixa": est["soma_faixa"],
            "pares": est["pares"],
            "primos": est["primos"],

            "linhas": est["linhas"],
            "hash_estrutura": est["hash_estrutura"],

            "vezes_gerado": 0,

            "acertos_11": 0,
            "acertos_12": 0,
            "acertos_13": 0,
            "acertos_14": 0,
            "acertos_15": 0,

            "score_medio_real": 0.0
        }

    mem = memoria_cache[chave]

    mem["vezes_gerado"] += 1

    vezes = mem["vezes_gerado"]

    score_antigo = float(
        mem.get(
            "score_medio_real",
            0
        )
    )

    novo_score = (
        (
            score_antigo * (vezes - 1)
        ) + peso
    ) / vezes

    mem["score_medio_real"] = round(
        novo_score,
        4
    )

    if acertos >= 11:
        mem[f"acertos_{acertos}"] += 1

    mem["updated_at"] = datetime.now().isoformat()


def sincronizar_memoria(
    supabase,
    memoria_cache
):

    print("🧠 Sincronizando memória...")

    inserts = []
    updates = []

    for mem in memoria_cache.values():

        if mem.get("id"):
            updates.append(mem)
        else:
            item = mem.copy()
            item.pop("id", None)
            inserts.append(item)

    if inserts:

        print(
            f"➕ Inserindo "
            f"{len(inserts)} novos cenários"
        )

        for i in range(
            0,
            len(inserts),
            50
        ):

            supabase.table(
                "memoria_cenarios"
            ).insert(
                inserts[i:i+50]
            ).execute()

    if updates:

        print(
            f"🔄 Atualizando "
            f"{len(updates)} cenários"
        )

        for item in updates:

            item_id = item["id"]

            payload = item.copy()
            payload.pop("id", None)

            supabase.table(
                "memoria_cenarios"
            ).update(
                payload
            ).eq(
                "id",
                item_id
            ).execute()


# ======================================================
# MAIN
# ======================================================

def main():

    supabase = get_supabase()

    print(
        "🏁 [v5.7.1-STABLE] "
        "Conferência Inteligente iniciada"
    )

    # ==================================================
    # RESULTADOS OFICIAIS
    # ==================================================

    oficiais = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso",
        desc=True
    ).limit(
        500
    ).execute()

    resultado_map = {}

    for item in (oficiais.data or []):

        nums = parse_numeros(
            item["dezenas"]
        )

        if nums:

            resultado_map[
                int(item["concurso"])
            ] = set(nums)

    print(
        f"📊 {len(resultado_map)} "
        f"concursos carregados"
    )

    # ==================================================
    # MEMÓRIA
    # ==================================================

    memoria_cache = carregar_memoria(
        supabase
    )

    # ==================================================
    # PALPITES PENDENTES
    # ==================================================

    pendentes = supabase.table(
        "palpites_validos"
    ).select(
        "*"
    ).eq(
        "processado",
        False
    ).execute()

    pendentes = (
        pendentes.data or []
    )

    print(
        f"📌 {len(pendentes)} "
        f"palpites pendentes"
    )

    updates_palpites = []

    for p in pendentes:

        try:

            concurso = int(
                str(
                    p["concurso_referencia"]
                ).strip()
            )

            if concurso not in resultado_map:
                continue

            nums = parse_numeros(
                p["numeros"]
            )

            if not nums:

                print(
                    f"⚠️ Palpite inválido "
                    f"ID={p['id']}"
                )

                continue

            acertos = len(
                set(nums)
                &
                resultado_map[
                    concurso
                ]
            )

            updates_palpites.append({
                "id": p["id"],
                "acertos": acertos,
                "processado": True,
                "conferido": True
            })

            atualizar_memoria_local(
                memoria_cache,
                nums,
                acertos
            )

        except Exception as e:

            print(
                f"⚠️ Erro ID="
                f"{p.get('id')} "
                f"-> {e}"
            )

    # ==================================================
    # UPDATE PALPITES
    # ==================================================

    if updates_palpites:

        print(
            f"🔄 Atualizando "
            f"{len(updates_palpites)} "
            f"palpites"
        )

        for item in updates_palpites:

            item_id = item["id"]

            payload = item.copy()

            payload.pop(
                "id",
                None
            )

            supabase.table(
                "palpites_validos"
            ).update(
                payload
            ).eq(
                "id",
                item_id
            ).execute()

    # ==================================================
    # SINCRONIZA MEMÓRIA
    # ==================================================

    sincronizar_memoria(
        supabase,
        memoria_cache
    )

    # ==================================================
    # CONSOLIDAÇÃO
    # ==================================================

    print(
        "📊 Consolidando "
        "resultados..."
    )

    todos = supabase.table(
        "palpites_validos"
    ).select(
        "data_referencia,"
        "concurso_referencia,"
        "tipo,"
        "versao_gerador,"
        "acertos"
    ).not_.is_(
        "acertos",
        "null"
    ).execute()

    consolidado = {}

    for p in (todos.data or []):

        concurso = int(
            p["concurso_referencia"]
        )

        tipo = (
            p.get("tipo")
            or "estatistico"
        ).strip()

        versao = (
            p.get(
                "versao_gerador"
            )
            or "legacy"
        ).strip()

        chave = (
            concurso,
            tipo,
            versao
        )

        if chave not in consolidado:

            data_ref = str(
                p.get(
                    "data_referencia"
                )
                or datetime.now().date()
            ).split(" ")[0]

            consolidado[
                chave
            ] = {

                "data_referencia": data_ref,

                "concurso_inicio": concurso,
                "concurso_fim": concurso,

                "tipo_palpite": tipo,
                "versao_gerador": versao,

                "qtd_palpites": 0,

                "score_ponderado": 0,

                "acertos_11": 0,
                "acertos_12": 0,
                "acertos_13": 0,
                "acertos_14": 0,
                "acertos_15": 0
            }

        ref = consolidado[chave]

        ref[
            "qtd_palpites"
        ] += 1

        acertos = p["acertos"]

        if acertos >= 11:

            ref[
                f"acertos_{acertos}"
            ] += 1

            ref[
                "score_ponderado"
            ] += PESO_ACERTOS.get(
                acertos,
                0
            )

    items = []

    for ref in consolidado.values():

        qtd = ref[
            "qtd_palpites"
        ]

        premiados = sum(
            ref.get(
                f"acertos_{i}",
                0
            )
            for i in range(
                11,
                16
            )
        )

        ref[
            "eficiencia"
        ] = round(
            (
                premiados / qtd
            ) * 100,
            2
        ) if qtd else 0

        ref[
            "score_medio"
        ] = round(
            ref[
                "score_ponderado"
            ] / qtd,
            4
        ) if qtd else 0

        for i in range(
            12,
            16
        ):

            ref[
                f"taxa_{i}"
            ] = round(
                (
                    ref.get(
                        f"acertos_{i}",
                        0
                    ) / qtd
                ) * 100,
                2
            ) if qtd else 0

        items.append(ref)

    print(
        f"🚀 Enviando "
        f"{len(items)} grupos"
    )

    for i in range(
        0,
        len(items),
        50
    ):

        try:

            supabase.table(
                "palpites_resultados_reais"
            ).upsert(
                items[i:i+50],
                on_conflict="concurso_inicio,tipo_palpite,versao_gerador"
            ).execute()

        except Exception as e:

            print(
                f"⚠️ Erro "
                f"consolidando: "
                f"{e}"
            )

    print(
        "✅ Processo "
        "concluído "
        "com sucesso"
    )


if __name__ == "__main__":
    main()

