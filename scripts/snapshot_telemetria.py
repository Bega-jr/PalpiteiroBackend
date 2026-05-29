import sys
import json
import numpy as np

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import (
    get_supabase
)


def media_segura(v):

    validos = [

        x for x in v
        if x is not None
    ]

    if not validos:
        return 0.0

    return float(np.mean(validos))


def dispersao(v):

    validos = [

        x for x in v
        if x is not None
    ]

    if len(validos) <= 1:
        return 0.0

    return float(np.std(validos))


def main():

    print("\n🧠 v1.0-snapshot-telemetria")
    print("==================================================")

    supabase = get_supabase()

    try:

        rows = (

            supabase
            .table("palpites_validos")
            .select("*")
            .order(
                "concurso_referencia",
                desc=True
            )
            .limit(7)
            .execute()
            .data
        )

    except Exception as e:

        print(f"❌ Erro leitura: {e}")
        return

    if not rows:

        print("⚠️ Nenhum palpite encontrado")
        return

    scores = []
    montecarlo = []
    estruturais = []
    clusters = []
    dezenas = []

    concurso = rows[0][
        "concurso_referencia"
    ]

    for r in rows:

        try:

            scores.append(
                float(r.get("score", 0))
            )

        except:
            pass

        try:

            montecarlo.append(
                float(
                    r.get(
                        "score_montecarlo",
                        0
                    )
                )
            )

        except:
            pass

        try:

            estruturais.append(
                float(
                    r.get(
                        "score_estrutural",
                        0
                    )
                )
            )

        except:
            pass

        try:

            clusters.append(
                int(
                    r.get(
                        "cluster_id",
                        -1
                    )
                )
            )

        except:
            pass

        try:

            nums = json.loads(
                r["numeros"]
            )

            dezenas.extend(nums)

        except:
            pass

    diversidade_global = len(
        set(dezenas)
    )

    clusters_unicos = len(
        set(clusters)
    )

    score_medio = media_segura(
        scores
    )

    mc_medio = media_segura(
        montecarlo
    )

    estrutural_medio = media_segura(
        estruturais
    )

    dispersao_scores = dispersao(
        scores
    )

    payload = {

        "concurso_referencia": concurso,

        "score_medio": round(
            score_medio,
            6
        ),

        "score_mc_medio": round(
            mc_medio,
            6
        ),

        "score_estrutural_medio": round(
            estrutural_medio,
            6
        ),

        "dispersao_scores": round(
            dispersao_scores,
            6
        ),

        "clusters_unicos": clusters_unicos,

        "diversidade_global": diversidade_global,

        "created_at": datetime.now().isoformat()
    }

    print("\n==================================================")
    print("📊 SNAPSHOT")
    print("==================================================")

    for k, v in payload.items():

        print(f"{k}: {v}")

    try:

        supabase.table(
            "snapshot_telemetria"
        ).insert(
            payload
        ).execute()

        print("\n✅ Snapshot persistido")

    except Exception as e:

        print(
            f"\n⚠️ Erro persistência: {e}"
        )


if __name__ == "__main__":
    main()
