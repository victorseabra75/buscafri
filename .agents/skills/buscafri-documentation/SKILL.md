---
name: buscafri-documentation
description: Manutenção da documentação técnica (SPEC, STATUS, TASKS, ADRs) e consistência do conhecimento do projeto.
---

# BuscaFri Documentation: Fonte de Verdade e Rastreabilidade

Esta skill orienta a manutenção e atualização dos documentos normativos e operacionais do projeto BuscaFri.

## Quando Usar
- Atualizar o status do projeto (`PROJECT_STATUS.md`).
- Registrar progresso em tarefas (`.agents/tasks.md`).
- Documentar decisões arquiteturais (ADRs em `.agents/governance/adr/`).
- Atualizar especificações técnicas (`SPEC.md`) após mudanças de contrato ou schema.

## Quando NÃO Usar
- Escrita de código-fonte (Python).
- Documentação externa (ex: README de marketing).

## Procedimento de Trabalho

### 1. Hierarquia de Verdade
- Consultar `docs/SOURCE_OF_TRUTH.md` para identificar qual documento prevalece.
- Código e testes são evidências de comportamento *implementado*. Documentos descrevem comportamento *esperado*.

### 2. Atualização de Status e Tarefas
- **PROJECT_STATUS.md**: Deve refletir o estado macro do sistema (o que está operacional, o que é backlog).
- **tasks.md**: Deve ser atualizado com o status real das atividades (`TODO`, `IN_PROGRESS`, `DONE`, `NEEDS_VALIDATION`).

### 3. Decisões Arquiteturais (ADRs)
- Criar ADR para mudanças significativas: alteração de banco (ex: migração para R2), novos padrões de segurança, mudanças em workflows de CI/CD.
- Usar formato: Título, Contexto, Decisão, Consequências.

### 4. Especificação Técnica (`SPEC.md`)
- Manter o mapeamento de tabelas e tipos de dados da Receita Federal atualizado.
- Documentar as rotas da API e schemas principais.

## Regras Obrigatórias
1. **Fatos vs. Desejos**: Diferenciar claramente o que já foi construído do que é planejamento futuro.
2. **Evitar Duplicação**: Se uma informação já existe no `SPEC.md`, não a repita integralmente no `CONTEXT.md`. Use referências.
3. **Sincronia**: Atualizar a documentação pertinente *junto* com a entrega da tarefa de código.

## Verificações de Conclusão
- [ ] `PROJECT_STATUS.md` atualizado.
- [ ] `tasks.md` reflete o estado final da tarefa.
- [ ] ADR criada se houver decisão estrutural.
- [ ] Referências quebradas corrigidas.

## Fontes
- Architecture Decision Records: https://adr.github.io/
- Diátaxis Framework: https://diataxis.fr/
