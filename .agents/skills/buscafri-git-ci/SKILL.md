---
name: buscafri-git-ci
description: Gestão de alterações, qualidade de código (Ruff), testes (Pytest) e integridade do pipeline de CI-CD.
---

# BuscaFri Git & CI: Qualidade e Fluxo de Trabalho

Esta skill orienta o versionamento de código e a manutenção da esteira de automação do BuscaFri.

## Quando Usar
- Realizar commits ou abrir PRs.
- Alterar configurações de Linter (`Ruff`) ou Testes (`Pytest`).
- Modificar workflows do GitHub Actions (`.github/workflows/`).
- Resolver falhas no pipeline de CI.

## Quando NÃO Usar
- Implementação de lógica de negócio (use `buscafri-executor-qa`).
- Planejamento de produto.

## Procedimento de Trabalho

### 1. Mensagens de Commit e Escopo
- Usar **Conventional Commits** (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Revisar o `git diff` antes do commit para garantir que apenas alterações do escopo da tarefa foram incluídas.

### 2. Qualidade Local (Pré-commit)
- Executar `uv run ruff check .` para garantir conformidade de estilo.
- Executar `uv run ruff format .` se necessário.
- Rodar a suíte de testes relevante: `uv run pytest tests/<arquivo>.py`.

### 3. GitHub Actions e CI
- **Jobs**: Entender a dependência entre `test` e `deploy`.
- **Secrets**: Garantir que o workflow tenha acesso aos segredos do R2 e VPS sem expô-los em logs.
- **Testes de Integração**: Identificados pelo marker `@pytest.mark.integration`. Só rodam se as credenciais estiverem presentes.

### 4. Proteção contra Versionamento Indevido
- Verificar `.gitignore` para: `.env`, `data/raw/`, `data/processed/`, `__pycache__`, `.pytest_cache/`, `uv.lock` (este último deve ser versionado, mas arquivos temporários de ambiente não).

## Regras Obrigatórias
1. **Sem Bypass**: Nunca use `continue-on-error: true` para mascarar falhas em testes obrigatórios ou linter.
2. **Testes Ignorados**: Declarar explicitamente no relatório de encerramento se algum teste foi pulado e o porquê (ex: falta de credenciais locais).
3. **Zero Secrets no Git**: Se detectar um segredo versionado no histórico, notificar imediatamente para limpeza (BFG/Filter-repo).

## Verificações de Conclusão
- [ ] `git status` limpo (sem arquivos temporários).
- [ ] `ruff check` aprovado.
- [ ] Testes aprovados no CI ou localmente.
- [ ] Mensagem de commit seguindo o padrão.

## Fontes
- Ruff Docs: https://docs.astral.sh/ruff/
- Pytest Documentation: https://docs.pytest.org/
- GitHub Actions: https://docs.github.com/en/actions
