PYTHONPATH=. python scripts/precalcular_estatisticas_numeros.py
PYTHONPATH=. python scripts/precalcular_estatisticas_diarias.py
Debug Environment: URL existe: False, KEY existe: False
Traceback (most recent call last):
  File "/workspaces/PalpiteiroBackend/scripts/precalcular_estatisticas_numeros.py", line 2, in <module>
    from app.core.supabase import supabase
  File "/workspaces/PalpiteiroBackend/app/core/supabase.py", line 13, in <module>
    raise ValueError("Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.")
ValueError: Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.
Debug Environment: URL existe: False, KEY existe: False
Traceback (most recent call last):
  File "/workspaces/PalpiteiroBackend/scripts/precalcular_estatisticas_diarias.py", line 2, in <module>
    from app.core.supabase import get_supabase
  File "/workspaces/PalpiteiroBackend/app/core/supabase.py", line 13, in <module>
    raise ValueError("Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.")
ValueError: Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.