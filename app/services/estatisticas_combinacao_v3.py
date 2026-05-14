from app.services.supabase_service import get_supabase
from collections import defaultdict
import json
import os
import math

CACHE_FILE = "tmp/padroes_cache_v3.json"


# ======================================================
# MÉTRICAS ESTRUTURAIS
# ======================================================
def extrair_metricas_jogo(nums):
    """
    Extrai estrutura estatística do jogo.
    """

    soma = sum(nums)

    pares = sum(
        1 for n in nums
        if n % 2 == 0
    )

    primos = sum(
        1 for n in nums
        if n in {2, 3, 5, 7, 11, 13, 17, 19, 23}
    )

    linhas = [0, 0, 0, 0, 0]

    for n in nums:

        idx = (n - 1) // 5

        if 0 <= idx < 5:
            linhas[idx] += 1

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "linhas": tuple(linhas)
    }


# ======================================================
# CACHE
# ======================================================
def salvar_cache(payload):

    os.makedirs(
        "tmp",
        exist_ok=True
    )

    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False
        )


def carregar_cache():

    if not os.path.exists(
        CACHE_FILE
    ):
        return None

    try:

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            )

    except Exception:
        return None


# ======================================================
# SCORE DE COMBINAÇÕES REAIS
# ======================================================
def calcular_score_combinacoes_reais(
    limite_concursos: int = 1000,
    usar_cache: bool = False
):
    """
    Aprende padrões reais.

    Retorna:
        scores
        metadata
    """

    # ==================================================
    # CACHE
    # ==================================================
    if usar_cache:

        cache = carregar_cache()

        if cache:

            print(
                "⚡ usando cache"
            )

            scores = {
                eval(k): v
                for k, v in cache["scores"].items()
            }

            metadata = {
                eval(k): v
                for k, v in cache["metadata"].items()
            }

            return scores, metadata

    supabase = get_supabase()

    print(
        f"📊 Aprendizado: últimos "
        f"{limite_concursos} concursos"
    )

    try:

        res = (
            supabase
            .table(
                "lotofacil_concursos"
            )
            .select(
                "dezenas"
            )
            .order(
                "concurso",
                desc=True
            )
            .limit(
                limite_concursos
            )
            .execute()
        )

    except Exception as e:

        print(
            f"❌ erro Supabase: {e}"
        )

        return {}, {}

    if not res.data:

        print(
            "⚠️ dados vazios"
        )

        return {}, {}

    freq_base = defaultdict(
        int
    )

    freq_rec = defaultdict(
        float
    )

    performance = defaultdict(
        lambda: {
            "hits_15": 0,
            "hits_14": 0,
            "hits_13": 0
        }
    )

    total = len(
        res.data
    )

    # ==================================================
    # LEITURA DOS CONCURSOS
    # ==================================================
    for idx, row in enumerate(
        res.data
    ):

        try:

            raw = row[
                "dezenas"
            ]

            if isinstance(
                raw,
                str
            ):

                nums = json.loads(
                    raw
                )

            else:
                nums = raw

            nums = sorted(
                int(n)
                for n in nums
            )

            if len(nums) != 15:
                continue

            m = extrair_metricas_jogo(
                nums
            )

            # reduz granularidade para criar reincidência real
            soma_bucket = round(
                m["soma"] / 20
            ) * 20
            
            pares_bucket = (
                m["pares"] // 2
            ) * 2
            
            primos_bucket = (
                m["primos"] // 2
            ) * 2
            
            linhas_bucket = tuple(
                min(4, x)
                for x in m["linhas"]
            )
            
            chave = (
                soma_bucket,
                pares_bucket,
                primos_bucket,
                linhas_bucket
            )

            # frequência bruta
            freq_base[
                chave
            ] += 1

            # recência
            peso_rec = (
                1 +
                (
                    1 -
                    (idx / total)
                )
            )

            freq_rec[
                chave
            ] += peso_rec

            # performance real baseada em reincidência
            freq_atual = freq_base[
                chave
            ]

            if freq_atual >= 4:

                performance[
                    chave
                ][
                    "hits_15"
                ] += 1

            elif freq_atual >= 2:

                performance[
                    chave
                ][
                    "hits_14"
                ] += 1

            else:

                performance[
                    chave
                ][
                    "hits_13"
                ] += 1

        except Exception:
            continue

    if not freq_base:
        return {}, {}

    # ==================================================
    # NORMALIZAÇÃO
    # ==================================================
    max_base = max(
        freq_base.values()
    )

    max_rec = max(
        freq_rec.values()
    )

    scores = {}
    metadata = {}

    for chave in freq_base:

        freq_score = (
            freq_base[
                chave
            ] / max_base
        )

        rec_score = (
            freq_rec[
                chave
            ] / max_rec
        )

        perf = performance[
            chave
        ]

        perf_score = (
            (
                perf[
                    "hits_15"
                ] * 1.0
            ) +
            (
                perf[
                    "hits_14"
                ] * 0.6
            ) +
            (
                perf[
                    "hits_13"
                ] * 0.3
            )
        )

        # evita favorecer padrões raros
        robustez = math.log(
            freq_base[
                chave
            ] + 1
        )

        final_score = (
            (
                freq_score * 0.45
            ) +
            (
                rec_score * 0.35
            ) +
            (
                perf_score * 0.20
            )
        ) * robustez

        scores[
            chave
        ] = round(
            final_score,
            6
        )

        metadata[
            chave
        ] = {

            "freq": freq_base[
                chave
            ],

            "hits_15": perf[
                "hits_15"
            ],

            "hits_14": perf[
                "hits_14"
            ],

            "hits_13": perf[
                "hits_13"
            ]
        }

    # ==================================================
    # CACHE
    # ==================================================
    payload = {

        "scores": {

            str(k): v

            for k, v in scores.items()
        },

        "metadata": {

            str(k): v

            for k, v in metadata.items()
        }
    }

    salvar_cache(
        payload
    )

    print(
        f"✅ Aprendizado concluído: "
        f"{len(scores)} padrões"
    )

    return scores, metadata


# ======================================================
# COMPATIBILIDADE LEGACY
# ======================================================
calcular_score_combinacoes = (
    calcular_score_combinacoes_reais
)
