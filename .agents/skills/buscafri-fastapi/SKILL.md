---
name: buscafri-fastapi
description: Desenvolvimento do backend BuscaFri, rotas, contratos Pydantic e integração com DuckDB/SlowAPI.
---

# BuscaFri FastAPI: Desenvolvimento de API Analítica

Esta skill orienta a criação e manutenção dos endpoints da API BuscaFri, garantindo performance e consistência dos contratos.

## Quando Usar
- Criar novos endpoints ou rotas.
- Alterar schemas Pydantic de requisição ou resposta.
- Integrar lógica de negócio com consultas DuckDB.
- Implementar filtros, paginação ou exportação de dados (CSV/XLSX).

## Quando NÃO Usar
- Alterações puramente de ETL/Scripting sem exposição via API.
- Configurações de infraestrutura Bare Metal.

## Procedimento de Trabalho

### 1. Organização e Padrões
- **Rotas**: Agrupadas em `app/api/v1/endpoints.py`.
- **Schemas**: Definidos em `app/schemas/`. Usar Pydantic V2.
- **Injeção de Dependência**: Usar para gerenciamento de conexões com o banco de dados.

### 2. Contratos e Validação
- **Preservação de Contratos**: Mudanças que quebram a API devem ser discutidas e documentadas como decisão arquitetural (ADR).
- **Padrões de Resposta**: Garantir consistência em códigos HTTP (200 para sucesso, 400 para erro de cliente, 429 para rate limit, 500 para erro interno).
- **Documentação**: Manter tags e descrições para OpenAPI (`/docs`).

### 3. Integração Analítica (DuckDB)
- Retornar dados em formato JSON ou via `StreamingResponse` para arquivos grandes (CSV/XLSX).
- Usar cursores ou paginação (`limit`, `offset` ou keyset) para evitar consumo excessivo de memória.
- Garantir fechamento de conexões se não forem gerenciadas pelo ciclo de vida da aplicação.

### 4. Rate Limiting
- Respeitar a integração com `SlowAPI`.
- Em testes, usar o `app.state.limiter` conforme estabelecido em `tests/test_api_v1.py`.

## Regras Obrigatórias
1. **Sem Mocks como Integração**: Testes de rotas devem, preferencialmente, validar a integração real com o DuckDB (usando dados de teste).
2. **Tratamento de Erros**: Usar `HTTPException` do FastAPI.
3. **Performance**: Operações pesadas do DuckDB não devem bloquear o loop de eventos (considerar uso de thread pools se necessário).

## Verificações de Conclusão
- [ ] Rota documentada no `/docs`.
- [ ] Schema Pydantic validado.
- [ ] Testes de integração em `tests/` aprovados.
- [ ] Rate limit verificado.

## Fontes
- FastAPI Docs: https://fastapi.tiangolo.com/
- SlowAPI: https://github.com/lauryndas/slowapi
- Pydantic V2: https://docs.pydantic.dev/latest/
