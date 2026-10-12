---
name: buscafri-security
description: Segurança de aplicação, gestão de secrets, validação de entradas e proteção de infraestrutura/CI-CD.
---

# BuscaFri Security: Proteção de Dados e Infraestrutura

Esta skill orienta a implementação de práticas de segurança no backend, pipelines de CI/CD e gerenciamento de acessos no ecossistema BuscaFri.

## Quando Usar
- Adicionar ou alterar variáveis de ambiente/secrets.
- Implementar validação de dados em rotas da API.
- Configurar CORS, Rate Limiting ou cabeçalhos de segurança.
- Revisar permissões de deploy ou acesso ao R2.

## Quando NÃO Usar
- Fix de bugs de lógica não relacionados a segurança.
- Formatação de código estético.

## Procedimento de Trabalho

### 1. Gestão de Secrets
- **Local**: Usar `.env` (incluído no `.gitignore`).
- **CI/CD**: Usar GitHub Secrets. Injetar via variáveis de ambiente no workflow.
- **VPS**: Permissões restritas (`chmod 600`) para arquivos de configuração e chaves SSH.
- **Regra de Ouro**: Nunca versionar segredos. Se um segredo for exposto, ele deve ser revogado imediatamente.

### 2. Validação e Sanitização (FastAPI)
- Usar tipos Pydantic rigorosos para todos os inputs de rotas.
- Tratar erros de forma opaca para o usuário (não expor stack traces ou detalhes do banco em respostas HTTP).
- Validar parâmetros de filtro (ex: UF deve ter 2 caracteres e estar no conjunto válido).

### 3. Rate Limiting e Proteção
- **SlowAPI**: Configurado globalmente ou por rota.
- **CORS**: Restringir origens permitidas em produção.
- **DuckDB**: Proteção contra injeção de SQL usando consultas parametrizadas (`conn.execute(query, params)`).

### 4. Infraestrutura e Deploy
- **Princípio do Menor Privilégio**: O usuário do deploy na VPS deve ter apenas as permissões necessárias.
- **GitHub Actions**: Revisar permissões de tokens e evitar scripts de terceiros não confiáveis.

## Regras Obrigatórias
1. **Proibição de Hardcode**: Nunca insira credenciais em código, YAML, testes ou documentação.
2. **Não Silenciar Alertas**: Não desabilite linters de segurança ou controles de rate limit apenas para "fazer o teste passar".
3. **Redação de Logs**: Garantir que segredos ou dados sensíveis de usuários não sejam impressos em logs (Systemd/Journalctl).

## Verificações de Conclusão
- [ ] `.env` e arquivos sensíveis não estão no `git status`.
- [ ] Inputs da API validados com Pydantic.
- [ ] Consultas DuckDB parametrizadas.
- [ ] Respostas de erro não vazam informações internas.

## Fontes
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- OWASP API Security: https://owasp.org/www-project-api-security/
