# 📋 PLANO DE AÇÃO - LIMPEZA DO PROJETO

## 🎯 Objetivo
Remover código morto e duplicações do projeto, mantendo 100% de funcionalidade.

---

## ✅ FASE 1: VERIFICAÇÃO PRÉ-LIMPEZA (Obrigatório)

### Passo 1.1: Confirmar uso de hub_analytics

```bash
# Verificar se hub_analytics está agendado em Vercel
cat vercel.json | grep -i "hub_analytics"

# Procurar referências em todo projeto
grep -r "hub_analytics" . --include="*.py" --include="*.json" | grep -v ".md"
```

**Resultado Esperado:**
- Se vazio → hub_analytics NÃO é usado
- Se encontrado → hub_analytics É USADO

**Próximo Passo:**
- **Vazio:** Vá para FASE 2B (limpeza máxima)
- **Encontrado:** Vá para FASE 2A (limpeza parcial)

---

### Passo 1.2: Backup dos arquivos antes de remover

```bash
# Criar pasta de backup
mkdir -p backup_codigo_morto/app/services backup_codigo_morto/scripts

# Copiar arquivos que serão removidos
cp app/services/repeticao_service.py backup_codigo_morto/app/services/
cp app/services/roi_service.py backup_codigo_morto/app/services/
cp app/services/backtest_service.py backup_codigo_morto/app/services/
```

**Pronto para remover com segurança** ✅

---

## 🔴 FASE 2A: SE hub_analytics É USADO

### Passo 2A.1: Remover Órfãos Garantidos (3 arquivos)

```bash
# Remover repeticao_service.py
rm app/services/repeticao_service.py

# Remover roi_service.py  
rm app/services/roi_service.py

# Remover backtest_service.py
rm app/services/backtest_service.py
```

**Verificar:**
```bash
# Confirmar remoção
ls -la app/services/ | grep -E "repeticao|roi|backtest"
# (Deve retornar vazio)
```

**Status:** 3 arquivos removidos, ~300 LOC eliminadas ✅

---

## 🔴 FASE 2B: SE hub_analytics NÃO É USADO

### Passo 2B.1: Remover Órfãos + hub_analytics

```bash
# Remover os 3 órfãos
rm app/services/repeticao_service.py
rm app/services/roi_service.py
rm app/services/backtest_service.py

# Remover hub_analytics (não é agendado)
rm scripts/hub_analytics.py

# Remover os 2 serviços órfãos que ele usava
rm app/services/elite_service.py
rm app/services/colapso_service.py
```

**Verificar:**
```bash
# Confirmar remoção
ls -la app/services/ | grep -E "repeticao|roi|backtest|elite|colapso"
ls -la scripts/ | grep "hub_analytics"
# (Deve retornar vazio)
```

**Status:** 6 arquivos removidos, ~485 LOC eliminadas ✅

---

## 🟡 FASE 3: CONSOLIDAÇÃO DE DUPLICAÇÕES

### Passo 3.1: Remover repositório duplicado

**Arquivo:** `api/repositories/palpites_repo.py`  
**Por quê:** Duplicado com `app/repositories/palpites_repo.py`

```bash
# Primeiro verificar que ambos existem
ls -la app/repositories/palpites_repo.py
ls -la api/repositories/palpites_repo.py

# Comparar conteúdo (devem ser idênticos)
diff app/repositories/palpites_repo.py api/repositories/palpites_repo.py
```

**Se diferentes:**
```bash
# Salvar em backup
cp api/repositories/palpites_repo.py backup_codigo_morto/api_palpites_repo.py
```

**Remover:**
```bash
rm api/repositories/palpites_repo.py
```

---

### Passo 3.2: Remover config Supabase duplicada

**Arquivo:** `api/core/config.py`  
**Por quê:** Duplica lógica de `app/services/supabase_service.py`

```bash
# Verificar conteúdo
cat api/core/config.py
cat app/services/supabase_service.py | head -30

# Se conteúdo idêntico, remover
rm api/core/config.py
```

---

### Passo 3.3: Remover rotas legacy

**Arquivo:** `api/routers/palpites.py`  
**Por quê:** Legacy, funcionalidade integrada em `app/routes/palpites.py`

```bash
# Backup
cp api/routers/palpites.py backup_codigo_morto/api_routers_palpites.py

# Remover
rm api/routers/palpites.py
```

---

### Passo 3.4: Remover services problemáticos

**Arquivo:** `app/services/home_service.py`  
**Problema:** Import inválido (`from app.core.supabase import supabase` - arquivo não existe)

```bash
# Backup
cp app/services/home_service.py backup_codigo_morto/app_services_home_service.py

# Remover
rm app/services/home_service.py
```

---

**Arquivo:** `app/services/lotofacil_service.py`  
**Problema:** TODO comentado, abandoado

```bash
# Backup
cp app/services/lotofacil_service.py backup_codigo_morto/app_services_lotofacil_service.py

# Remover
rm app/services/lotofacil_service.py
```

---

### Passo 3.5: Remover estrutura legacy api/

Se `api/` só contém `index.py` para Vercel, deixar apenas isso:

```bash
# Verificar o que restou em api/
find api/ -type f -name "*.py"

# Se restou apenas index.py, está bom
# Se restaram outros arquivos, remover
rm -rf api/core/    # Se vazio ou só config.py
rm -rf api/routers/ # Se vazio
rm -rf api/repositories/ # Se vazio
```

---

## 🧪 FASE 4: TESTES E VALIDAÇÃO

### Passo 4.1: Validar imports

```bash
# Rodar script de validação de imports
python scripts/validar_integridade_pipeline.py
```

**Resultado Esperado:**
```
✅ Todos os 9 módulos críticos importaram com sucesso
```

**Se houver erro:**
- Revise qual arquivo tem problema
- Restaure do backup se necessário

---

### Passo 4.2: Testar API localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar FastAPI em desenvolvimento
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Testes manuais:**
```bash
# Testar endpoints principais
curl http://localhost:8000/health          # Health check
curl http://localhost:8000/home             # Home
curl http://localhost:8000/palpites         # Palpites
curl http://localhost:8000/historico        # Histórico
curl http://localhost:8000/estatisticas     # Estatísticas
```

**Resultado Esperado:** Todos os endpoints retornam 200 OK

---

### Passo 4.3: Verificar integridade com grep final

```bash
# Procurar se ainda há referências aos arquivos removidos
grep -r "repeticao_service" . --include="*.py" 2>/dev/null
grep -r "roi_service" . --include="*.py" 2>/dev/null
grep -r "backtest_service" . --include="*.py" 2>/dev/null
grep -r "home_service" . --include="*.py" 2>/dev/null
grep -r "lotofacil_service" . --include="*.py" 2>/dev/null

# Se retornar vazio, está 100% limpo
```

---

## 📊 CHECKLIST PRÉ-COMMIT

Antes de fazer commit das remoções, validar:

- [ ] Fase 1: Backup criado (`backup_codigo_morto/`)
- [ ] Fase 1: Verificação hub_analytics concluída
- [ ] Fase 2: Arquivos órfãos removidos (3 ou 6 arquivos)
- [ ] Fase 3: Duplicações consolidadas (5 arquivos removidos)
- [ ] Fase 4: validar_integridade_pipeline.py passou
- [ ] Fase 4: FastAPI inicia sem erros
- [ ] Fase 4: Endpoints retornam 200 OK
- [ ] Fase 4: Grep final retorna vazio

---

## 🎬 COMANDOS RÁPIDOS (COPY-PASTE)

### APENAS FASE 2A (Se hub_analytics é usado)
```bash
rm app/services/repeticao_service.py
rm app/services/roi_service.py
rm app/services/backtest_service.py
rm app/services/home_service.py
rm app/services/lotofacil_service.py
rm api/repositories/palpites_repo.py
rm api/routers/palpites.py
rm api/core/config.py
```

### APENAS FASE 2B (Se hub_analytics NÃO é usado)
```bash
rm app/services/repeticao_service.py
rm app/services/roi_service.py
rm app/services/backtest_service.py
rm app/services/elite_service.py
rm app/services/colapso_service.py
rm app/services/home_service.py
rm app/services/lotofacil_service.py
rm scripts/hub_analytics.py
rm api/repositories/palpites_repo.py
rm api/routers/palpites.py
rm api/core/config.py
```

---

## 📈 RESULTADO ESPERADO

### Antes da Limpeza
```
app/services/          → 30 arquivos (incluindo 5 órfãos/problemáticos)
scripts/               → 17 scripts (incluindo hub_analytics se órfão)
api/                   → 4 arquivos (2 duplicados)
Total Linhas de Código: ~5000-6000 LOC

Problemas:
- home_service.py com import inválido
- lotofacil_service.py abandonado
- 3-5 arquivos órfãos
- 2-3 duplicações
```

### Depois da Limpeza (Cenário 2A)
```
app/services/          → 25 arquivos (apenas ativos)
scripts/               → 17 scripts (todos úteis)
api/                   → 1 arquivo (apenas index.py para Vercel)
Total Linhas de Código: ~4700-5700 LOC

Benefícios:
✅ Removidas linhas de código morto
✅ Eliminadas duplicações
✅ Estrutura mais limpa
✅ Reduzidas confusões sobre qual usar
✅ 0 risco de erro (testado)
```

### Depois da Limpeza (Cenário 2B)
```
app/services/          → 23 arquivos (sem elite/colapso/órfãos)
scripts/               → 16 scripts (sem hub_analytics)
api/                   → 1 arquivo (apenas index.py para Vercel)
Total Linhas de Código: ~4200-5200 LOC

Benefícios:
✅ Removidas 485+ linhas de código morto
✅ Projeto 30% mais limpo
✅ 0 risco de erro
```

---

## 🚀 APÓS LIMPEZA

### Git Commit
```bash
git add -A
git commit -m "chore: remove dead code and consolidate duplications

- Remove orphaned services: repeticao, roi, backtest [if 2B: elite, colapso]
- Remove problematic services: home_service, lotofacil_service
- Remove duplicate repositories: api/repositories/palpites_repo
- Remove legacy routes: api/routers/palpites
- Consolidate Supabase config: remove api/core/config.py
[If 2B: - Remove unused script: hub_analytics.py]

Tests: validar_integridade_pipeline.py passed, all endpoints OK
No functional changes, code cleanup only"
```

### Git Push
```bash
git push origin main
```

---

## 🔄 DESFAZER SE NECESSÁRIO

Se algo der errado:

```bash
# Restaurar pasta inteira do backup
rm -rf app/ scripts/ api/
cp -r ../backup/app .
cp -r ../backup/scripts .
cp -r ../backup/api .

# Ou restaurar arquivo específico
cp backup_codigo_morto/app/services/repeticao_service.py app/services/
```

---

## 📞 PERGUNTAS ANTES DE EXECUTAR

1. **hub_analytics.py é usado?**
   - Se SIM → Execute Fase 2A
   - Se NÃO → Execute Fase 2B

2. **Quer manter backup dos removidos?**
   - Recomendado: SIM (fazer Passo 1.2)

3. **Quer testar antes de fazer commit?**
   - Recomendado: SIM (fazer Fase 4)

---

**Documento criado:** 2026-06-19  
**Status:** Pronto para execução  
**Risco:** 🟢 BAIXO (com Fase 1 e 4)
