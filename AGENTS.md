# BuscaFri --- Regras de Governança para Agentes

## 1. Princípios
O projeto segue a regra: **Ler → Entender → Verificar → Planejar → Implementar → Testar → Revisar → Documentar.**

**Leitura Seletiva (Obrigatória):** Não carregue todo o projeto. Identifique a tarefa e carregue apenas o necessário.

**AGENTS.md define regras de trabalho e roteia o agente para as fontes apropriadas; não substitui código, testes, configuração ou documentação técnica especializada.**

## 2. Fluxo de Trabalho
1. **Classifique a tarefa** (Backend, ETL, UI, Infra, etc.).
2. **Consulte** `docs/SOURCE_OF_TRUTH.md` para encontrar a fonte primária.
3. **Leia apenas** os arquivos fundamentais (ex: `CONTEXT.md`, código, teste).
4. **Selecione somente as skills necessárias à tarefa**, evitando carregar skills irrelevantes.

### Roteador de Contexto
| Tipo | Contexto inicial sugerido |
| :--- | :--- |
| Backend | `CONTEXT.md` + código/testes |
| ETL | `CONTEXT.md` + scripts ETL + testes |
| Frontend | `CONTEXT.md` + código UI |
| Infra | `CONTEXT.md` + workflows + scripts |
| Bug | Skill diagnóstico + código/teste relacionado |

### Catálogo Oficial de Skills do BuscaFri
As skills oficiais e validadas para este projeto são:
- `buscafri-planner`: Planejamento de funcionalidades, pesquisa de esquemas e geração de PRDs/Specs.
- `buscafri-executor-qa`: Execução de tickets individuais, TDD e validação de QA com Pytest.
- `diagnosing-bugs`: Diagnóstico estruturado em 6 fases para bugs complexos e regressões.
- `tdd`: Referência metodológica para o ciclo Red-Green-Refactor e seams de teste.
- `code-review`: Revisão de diffs em dois eixos (Standards e Spec), com adaptação local para ausência de issue tracker externo.
- `buscafri-duckdb-r2`: Consultas analíticas, ETL, Parquet e acesso remoto ao Cloudflare R2.
- `buscafri-security`: Segurança de aplicação, secrets, validação de entradas e proteção de infra/CI-CD.
- `buscafri-fastapi`: Desenvolvimento consistente do backend, rotas e contratos da API.
- `buscafri-git-ci`: Gestão de alterações, qualidade automatizada e integridade do pipeline.
- `buscafri-documentation`: Manutenção de SPEC, STATUS, TASKS e ADRs.

### Roteador de Contexto
| Tipo | Contexto inicial sugerido | Skill Recomendada |
| :--- | :--- | :--- |
| Planejamento / Spec | `CONTEXT.md` + `SPEC.md` | `buscafri-planner` |
| Backend / API | `CONTEXT.md` + código/testes | `buscafri-fastapi`, `buscafri-executor-qa`, `tdd` |
| ETL / Dados / R2 | `CONTEXT.md` + scripts ETL + testes | `buscafri-duckdb-r2`, `buscafri-executor-qa` |
| Frontend / UI | `CONTEXT.md` + código UI | `buscafri-executor-qa` |
| Infra / CI-CD | `CONTEXT.md` + workflows + scripts | `buscafri-git-ci`, `buscafri-security` |
| Segurança / Secrets | `.env` + workflows + ADRs | `buscafri-security` |
| Diagnóstico de Bug | Skill diagnóstico + código/teste relacionado | `diagnosing-bugs`, `tdd` |
| Code Review | Diff atual + padrões do projeto | `code-review` |
| Documentação | `PROJECT_STATUS.md` + `tasks.md` | `buscafri-documentation` |

## 3. Fontes de Verdade
Consulte `docs/SOURCE_OF_TRUTH.md`. Se houver divergência entre documentação e implementação: **não corrija automaticamente**. Registre, verifique código/testes e, se persistir, marque como **NÃO VERIFICADO**.

## 4. Diretrizes Técnicas
* **Segurança**: Nunca coloque secrets no código.
* **Infraestrutura**: Respeite os limites da VM `e2-micro`.
* **Dados**: Use processamento em *streaming* e consultas parametrizadas (nunca concatene SQL).

## 5. Implementação
* **Processo**: Entenda → Planeje → Implemente → Valide.
* **Testes**: Execute apenas os testes relevantes. Regressão total apenas na finalização.
* **Documentação**: Atualize apenas se o escopo da tarefa exigir.

## 6. Git
Use mensagens convencionais (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). Nunca versionar `.env`, credenciais ou artefatos temporários.

## 7. Protocolo de Encerramento
Relate obrigatoriamente:
* O que mudou e por que;
* Arquivos alterados;
* Testes executados e resultado;
* Documentação atualizada (se necessário);
* Decisões (ADR, se aplicável);
* Pontos não verificados/bloqueios.

*Nota: Não encerre uma alteração de código com testes obrigatórios/relevantes falhando sem registrar explicitamente o bloqueio e sua causa.*
