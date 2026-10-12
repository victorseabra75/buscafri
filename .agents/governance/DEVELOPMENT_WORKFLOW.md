# BuscaFri --- Workflow de Desenvolvimento Assistido por LLM

## 1. Ciclo oficial

``` text
CONTEXTO
   ↓
DOCUMENTAÇÃO
   ↓
SKILLS
   ↓
CÓDIGO + TESTES
   ↓
PLANO
   ↓
IMPLEMENTAÇÃO
   ↓
LINT
   ↓
TESTES
   ↓
REVISÃO DO DIFF
   ↓
DOCUMENTAÇÃO
   ↓
STATUS / ADR
   ↓
COMMIT / PR
```

Nenhuma etapa deve ser pulada sem justificativa.

## 2. Pré-voo obrigatório

Antes de escrever código, o agente deve verificar:

-   `AGENTS.md`
-   `.agents/CONTEXT.md`
-   `.agents/tasks.md`
-   `.agents/skills/` relevante
-   `README.md`
-   `PROJECT_STATUS.md`
-   `data/docs/` relevante
-   código relacionado
-   testes relacionados
-   estado do Git

## 3. Pequenas tarefas

Preferir uma tarefa por vez.

Exemplo:

``` text
Task 4.3A — centralizar configuração
Task 4.3B — adicionar testes de configuração
Task 4.3C — atualizar documentação
```

Evitar prompts que solicitem simultaneamente ETL + R2 + API + frontend +
deploy.

## 4. Implementação

O agente deve:

-   preservar comportamento não relacionado;
-   evitar refatoração ampla;
-   reutilizar abstrações existentes;
-   seguir padrões já presentes;
-   usar nomes existentes;
-   parametrizar SQL;
-   manter compatibilidade com testes.

## 5. Validação

Ordem recomendada:

``` bash
uv run ruff check .
uv run pytest tests/<testes-da-tarefa>.py -vv
uv run pytest -vv
```

Se houver uma task Poe equivalente:

``` bash
uv run poe dev
```

## 6. Revisão

Antes de considerar pronto:

``` bash
git diff --check
git status --short
git diff --stat
git diff
```

Perguntas:

-   alterei algo fora do escopo?
-   criei comportamento não solicitado?
-   deixei hardcode?
-   introduzi dependência de R2 em teste local?
-   quebrei configuração de produção?
-   preciso atualizar documentação?
-   surgiu uma decisão arquitetural?

## 7. Registro da alteração

Para alteração simples:

-   atualizar `PROJECT_STATUS.md` quando necessário;
-   atualizar `.agents/tasks.md`;
-   registrar no changelog quando o projeto adotar esse arquivo.

Para decisão arquitetural:

-   criar/atualizar ADR.

## 8. Encerramento

A resposta final da LLM deve conter:

``` text
Resumo
Arquivos alterados
Testes executados
Resultados
Documentação atualizada
Decisões tomadas
Riscos/bloqueios
Próximo passo
```

### Protocolo Obrigatório de Relatório de Encerramento (Pós-Tarefa)

Ao final de cada tarefa, o agente deve registrar:

1. **Comprovação de Execução e Skills**
   - **Skills consultadas**: nomes e motivo da consulta.
   - **Skills efetivamente aplicadas**: nome e evidência concreta de aplicação.
   - **Arquivos alterados**: lista dos arquivos modificados.
   - **Comandos executados**: comandos completos e resultados reais.
   - **Testes executados**: quantidade, resultado e escopo.
   - **Testes ignorados ou não executados**: motivo explícito.
   - **Validações de segurança**: verificações realmente executadas e limitações.
   - **Limitações e riscos remanescentes**: itens não verificados ou dependentes de ambiente externo.
   - **Documentação atualizada**: arquivos alterados ou justificativa para não alterar.
   - **Ações não realizadas**: informar explicitamente quando não houve push, deploy ou acesso ao R2.
