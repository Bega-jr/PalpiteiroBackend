# Palpiteiro Backend

API FastAPI para resultados, estatísticas e histórico de palpites da Lotofácil.

## Executar localmente

Requer Python 3.12 ou superior. Instale as dependências e configure as variáveis:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Defina `SUPABASE_URL` e uma chave Supabase no ambiente ou em `.env` na raiz do
repositório. O backend aceita `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
ou `SUPABASE_KEY`. Nunca publique uma chave de serviço no frontend.

```bash
uvicorn app.main:app --reload
```

A documentação interativa fica em `/docs`.

## Histórico do usuário

`GET /historico/` aceita `page` (padrão `1`) e `limit` (padrão `50`, máximo
`100`) e retorna a página solicitada. `GET /historico/resumo` calcula os totais
percorrendo os registros em lotes.

## CORS

As origens de produção e desenvolvimento listadas em `app/main.py` são aceitas
por padrão. Para adicionar origens de desenvolvimento, defina
`CORS_ALLOWED_ORIGINS` como uma lista separada por vírgulas. A lista não aceita
origens curinga.

## Testes

```bash
python -m unittest discover -s tests
```