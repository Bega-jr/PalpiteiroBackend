from supabase import create_client
import os

# Busca a URL
url = os.getenv("SUPABASE_URL")

# Busca a chave tentando os nomes mais comuns que você configurou
# O sinal de 'or' faz com que ele tente a primeira, se for nula, tenta a segunda
key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# Verificação de segurança para ajudar no debug se algo faltar
if not url or not key:
    raise ValueError(f"Erro de configuração: URL ou KEY não encontradas. URL: {bool(url)}, KEY: {bool(key)}")

supabase = create_client(url, key)
