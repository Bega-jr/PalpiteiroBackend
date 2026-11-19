# Guia rápido

## Estrutura

- `app/`: API e serviços de aplicação.
- `scripts/`: geração de palpites, atualização de resultados e análise de desempenho.
- `.github/workflows/`: pipeline diário e execução manual.
- `tests/`: testes automatizados.

## Testes

Execute a suíte com:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Automação

O workflow em `.github/workflows/atualizar-estatisticas-diarias.yml` atualiza os resultados oficiais, confere palpites pendentes, processa feedback e gera o próximo portfólio. A aprovação estrutural do portfólio não representa garantia de acerto.

O [resumo executivo](RESUMO_EXECUTIVO.md) documenta uma análise de 2026-06-19 e pode estar desatualizado. Consulte o código e o workflow para confirmar o comportamento atual antes de executar recomendações.
