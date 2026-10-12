---
name: buscafri-duckdb-r2
description: Consultas analíticas, ETL, Parquet e acesso remoto via DuckDB + httpfs ao Cloudflare R2 (S3).
---

# BuscaFri DuckDB & R2: Consultas, ETL e Streaming

Esta skill orienta operações de dados utilizando DuckDB com extensão `httpfs` para leitura direta de arquivos Parquet hospedados no Cloudflare R2.

## Quando Usar
- Criar ou depurar consultas SQL no DuckDB.
- Operações de ETL (CSV -> Parquet).
- Validar schemas de arquivos Parquet locais ou remotos.
- Configurar conexão S3/R2 no DuckDB.

## Quando NÃO Usar
- Tarefas de UI (Streamlit) sem relação com dados.
- Configuração de roteamento da API.
- Planejamento de funcionalidades (use `buscafri-planner`).

## Procedimento de Trabalho

### 1. Configuração de Conexão (Segura)
- Carregar `httpfs`.
- Usar variáveis de ambiente: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
- Configurar: `s3_url_style='path'`, `s3_use_ssl='true'`.
- **PROIBIDO**: Imprimir credenciais em logs, erros ou no `SKILL.md`.

### 2. Padrões de Consulta e Performance
- **Projeção de Colunas**: Nunca use `SELECT *` em tabelas grandes. Especifique as colunas.
- **Filtros (Pushdown)**: Aplique filtros `WHERE` para reduzir a leitura de dados do R2.
- **Particionamento Hive**: Aproveite a estrutura `uf={UF}`. DuckDB filtra automaticamente diretórios se a UF estiver no `WHERE`.
- **Memória**: Respeite o limite da VPS (1GB). Use `SET max_memory='400MB'`.
- **JOINs**: Realize JOINs entre `empresas` e `estabelecimentos` pela chave `cnpj_basico`.

### 3. Validação de Dados
- Validar tipos físicos (ex: `VARCHAR` observado para colunas de ID).
- Confirmar contagem de linhas após ETL.
- Testar integridade física do Parquet (`DESCRIBE SELECT * FROM '...'`).

## Regras Obrigatórias
1. **Zero Vazamento**: Nunca exponha chaves ou tokens.
2. **Sem Escrita Não Autorizada**: Não execute `COPY ... TO 's3://...'`, `DELETE` ou sincronização destrutiva sem autorização explícita.
3. **Falhas Explícitas**: Se o R2 falhar, o erro deve ser reportado. Não crie fallbacks silenciosos para dados locais que possam mascarar problemas de conexão.
4. **Leitura Mínima**: Evite glob patterns genéricos (`**/*.parquet`) se puder filtrar por UF ou pasta específica.

## Verificações de Conclusão
- [ ] Consulta retorna os dados esperados.
- [ ] Schema validado contra `SPEC.md` ou JSON schemas em `data/schema/`.
- [ ] Uso de memória dentro dos limites.
- [ ] Nenhuma credencial presente em saídas ou arquivos.

## Fontes
- DuckDB S3 Import: https://duckdb.org/docs/guides/import/s3_import
- DuckDB Parquet: https://duckdb.org/docs/data/parquet/overview
