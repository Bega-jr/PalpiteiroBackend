        "concurso": concurso_ref
    }

# ======================================================
# ENTRYPOINT (Modo isolado para testes manuais no terminal)
# ======================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--modo",
        default="moderado",
        choices=[
            "conservador",
            "moderado",
            "agressivo"
        ]
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Força a regeneração ignorando travas de banco"
    )

    args = parser.parse_args()

    try:

        sb = get_supabase()

        from scripts.processamento_diario_lotofacil import (
            carregar_historico
        )

        hist = carregar_historico()

        concurso_ref = (
            int(hist[-1]["concurso"]) + 1
        )

        if (
            not args.force
            and concurso_ja_processado(
                sb,
                concurso_ref
            )
        ):
            print(
                f"ℹ️ Concurso {concurso_ref} "
                f"já processado no banco."
            )
            sys.exit(0)

        print(
            "⚙️ Executando engine "
            "em modo de teste isolado..."
        )

        resultado_teste = executar_motor_geracao(
            modo_variacao=args.modo
        )

        if resultado_teste:

            payload_teste = [
                p.copy()
                for p in resultado_teste["palpites"]
            ]
        
            print("\n===== DEBUG PAYLOAD =====")
            print(
                json.dumps(
                    payload_teste[0],
                    indent=2,
                    default=str
                )
            )

            res = sb.table(
                "palpites_validos"
            ).upsert(
                payload_teste,
                on_conflict="concurso_referencia,indice_palpite"
            ).execute()

            print("\n===== DEBUG UPSERT =====")
            print(res)

            print(
                f"✅ [TESTE BUCKET] "
                f"{len(payload_teste)} "
                f"palpites gravados no banco."
            )

            print(
                "\n📲 TELEGRAM_PAYLOAD_START"
            )

            print(
                montar_msg_telegram(
                    resultado_teste["concurso"],
                    resultado_teste["linhas_telegram"]
                )
            )

            print(
                "📲 TELEGRAM_PAYLOAD_END"
            )

    except Exception:
        import traceback
        traceback.print_exc()
        raise

