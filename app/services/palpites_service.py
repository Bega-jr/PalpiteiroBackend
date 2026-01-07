from datetime import date
from app.services.supabase_service import get_supabase

# =====================================================
# SERVIÇO DE PALPITES (VERSÃO FINAL CORRIGIDA 2026)
# =====================================================

def obter_palpite_fixo_publico():
    """
    Busca o palpite de índice 0 (Fixo) mais recente disponível.
    """
    try:
        supabase = get_supabase()
        
        # Busca especificamente o índice 0 ordenando pela data mais nova
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("indice_palpite", 0)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        # O Supabase retorna uma lista. Verificamos se ela tem conteúdo.
        if not resp.data or len(resp.data) == 0:
            print("⚠️ Service: Nenhum palpite fixo encontrado no banco.")
            return None

        # ACESSO AO PRIMEIRO ITEM [0]
        registro = resp.data[0]
        
        return {
            "status": "ok",
            "data_referencia": str(registro.get("data_referencia")),
            "numeros": registro.get("numeros"),
            "metricas": registro.get("metricas", {})
        }
    except Exception as e:
        print(f"❌ Erro crítico no Service (Fixo): {repr(e)}")
        return None

def obter_palpites_estatisticos_publico():
    """
    Busca os palpites estatísticos da data mais recente disponível.
    """
    try:
        supabase = get_supabase()
        
        # 1. Identifica a data mais recente com registros
        data_resp = (
            supabase.table("palpites_validos")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        
        if not data_resp.data or len(data_resp.data) == 0:
            print("⚠️ Service: Nenhuma data de palpite encontrada.")
            return []
            
        # EXTRAÇÃO DA DATA DO PRIMEIRO ITEM [0]
        ultima_data = data_resp.data[0]["data_referencia"]
        print(f"📅 Service: Carregando palpites da data {ultima_data}")

        # 2. Busca todos os palpites daquela data específica (exceto o fixo 0)
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("data_referencia", ultima_data)
            .gt("indice_palpite", 0)
            .order("indice_palpite", desc=False)
            .execute()
        )

        if not resp.data:
            return []

        palpites = []
        for r in resp.data:
            metricas = r.get("metricas") if isinstance(r.get("metricas"), dict) else {}
            
            palpites.append({
                "indice": r.get("indice_palpite"),
                "numeros": r.get("numeros"),
                "tipo": r.get("tipo"),
                "score": metricas.get("score", 0.85),
                "soma": r.get("soma_total"),
                "pares": r.get("pares")
            })
        
        return palpites
    except Exception as e:
        print(f"❌ Erro crítico no Service (Estatísticos): {repr(e)}")
        return []

