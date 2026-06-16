import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from scripts.processamento_diario_lotofacil import extrair_estrutura


# ======================================================
# AUX
# ======================================================

def parse_numeros(valor):

    if not valor:
        return []

    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):

        try:
            return [int(x) for x in json.loads(valor)]
        except:
            return []

    return []


# ======================================================
# MAIN
# ======================================================

def main():

    supabase = get_supabase()

    print(
        "\n🧠 Recalibrando memória estrutural..."
    )

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(300)
        .execute()
        .data
    )

    mapa_resultados = {}

    for row in concursos:
    
        concurso = int(row["concurso"])
    
        mapa_resultados[
            concurso
        ] = set(
            parse_numeros(
                row["dezenas"]
            )
        )
    
    print(f"\n📊 Concursos carregados: {len(mapa_resultados)}")
    
    for c in sorted(mapa_resultados.keys(), reverse=True)[:20]:
        print(f"Concurso carregado: {c}")

    palpites = (

        supabase
        .table("palpites_validos")
        .select(
            "concurso_referencia,numeros,acertos,conferido"
        )
        .eq(
            "conferido",
            True
        )
        .execute()
        .data

    )

    print(
        f"📊 Palpites conferidos: {len(palpites)}"
    )

    por_concurso = {}

    for row in palpites:

        concurso = int(
            row["concurso_referencia"]
        )

        por_concurso.setdefault(
            concurso,
            []
        ).append(row)

    print(f"\n📊 Concursos com palpites: {len(por_concurso)}")

    for c in sorted(por_concurso.keys(), reverse=True):
        print(f"Palpite encontrado para concurso {c}")

    memoria = {}

    agora = datetime.now().isoformat()

    # ======================================================
    # PROCESSAMENTO
    # ======================================================

    for concurso, jogos in por_concurso.items():

        if concurso not in mapa_resultados:
            print(
                f"❌ Concurso {concurso} não encontrado em mapa_resultados"
            )
            continue
    
        print(
            f"✅ Concurso {concurso} encontrado"
        )
        resultado = mapa_resultados[
            concurso
        ]

        estrutura = extrair_estrutura(
            list(resultado)
        )

        hash_est = estrutura[
            "hash_estrutura"
        ]

        acertos_lista = []

        for jogo in jogos:

            if jogo.get("acertos") is not None:

                acertos_lista.append(
                    int(
                        jogo["acertos"]
                    )
                )

            else:

                nums = set(
                    parse_numeros(
                        jogo["numeros"]
                    )
                )

                acertos_lista.append(
                    len(
                        nums &
                        resultado
                    )
                )

        if not acertos_lista:
            continue

        media = (
            sum(acertos_lista)
            / len(acertos_lista)
        )

        melhor = max(
            acertos_lista
        )

        pior = min(
            acertos_lista
        )

        dispersao = (
            melhor - pior
        )

        estabilidade = max(
            0,
            1 - (
                dispersao / 15
            )
        )

        sobrevivencia = (
            1
            if media >= 10
            else 0
        )

        previsibilidade = (
            estabilidade
        )

        contextual = (

            media * 0.60 +

            previsibilidade * 0.20 +

            sobrevivencia * 10 * 0.20

        )

        if hash_est not in memoria:

            memoria[
                hash_est
            ] = {

                "estrutura":
                    estrutura,

                "medias":
                    [],

                "estabilidades":
                    [],

                "dispersoes":
                    [],

                "sobrevivencias":
                    [],

                "contextuais":
                    [],

                "previsibilidades":
                    [],

                "ultima_aparicao":
                    concurso
            }

        bloco = memoria[
            hash_est
        ]

        bloco["medias"].append(
            media
        )

        bloco[
            "estabilidades"
        ].append(
            estabilidade
        )

        bloco[
            "dispersoes"
        ].append(
            dispersao
        )

        bloco[
            "sobrevivencias"
        ].append(
            sobrevivencia
        )

        bloco[
            "contextuais"
        ].append(
            contextual
        )

        bloco[
            "previsibilidades"
        ].append(
            previsibilidade
        )

        bloco[
            "ultima_aparicao"
        ] = max(
            bloco[
                "ultima_aparicao"
            ],
            concurso
        )

    print(
        f"📊 Estruturas encontradas: {len(memoria)}"
    )

    # ======================================================
    # UPDATE
    # ======================================================

    atualizados = 0

    for hash_est, dados in memoria.items():

        estrutura = dados[
            "estrutura"
        ]

        payload = {

            "hash_estrutura":
                hash_est,

            "soma_faixa":
                estrutura[
                    "soma_faixa"
                ],

            "pares":
                estrutura[
                    "pares"
                ],

            "primos":
                estrutura[
                    "primos"
                ],

            "linhas":
                estrutura[
                    "linhas"
                ],

            "vezes_gerado":
                len(
                    dados["medias"]
                ),

            "score_medio_real":
                round(
                    sum(
                        dados["medias"]
                    )
                    /
                    len(
                        dados["medias"]
                    ),
                    4
                ),

            "estabilidade_media":
                round(
                    sum(
                        dados["estabilidades"]
                    )
                    /
                    len(
                        dados["estabilidades"]
                    ),
                    6
                ),

            "dispersao_media":
                round(
                    sum(
                        dados["dispersoes"]
                    )
                    /
                    len(
                        dados["dispersoes"]
                    ),
                    6
                ),

            "taxa_sobrevivencia":
                round(
                    sum(
                        dados["sobrevivencias"]
                    )
                    /
                    len(
                        dados["sobrevivencias"]
                    ),
                    6
                ),

            "score_contextual":
                round(
                    sum(
                        dados["contextuais"]
                    )
                    /
                    len(
                        dados["contextuais"]
                    ),
                    6
                ),

            "score_previsibilidade":
                round(
                    sum(
                        dados[
                            "previsibilidades"
                        ]
                    )
                    /
                    len(
                        dados[
                            "previsibilidades"
                        ]
                    ),
                    6
                ),

            "ultima_aparicao":
                dados[
                    "ultima_aparicao"
                ],

            "ultima_atualizacao_contextual":
                agora,

            "updated_at":
                agora
        }

        (
            supabase
            .table("memoria_cenarios")
            .upsert(
                payload,
                on_conflict="hash_estrutura"
            )
            .execute()
        )

        atualizados += 1

    print(
        f"\n✅ Estruturas recalibradas: {atualizados}"
    )


if __name__ == "__main__":
    main()
