# BuscaFri — Status do Projeto (PROJECT_STATUS.md)

## 1. Contexto & Arquitetura
**Objetivo do Projeto**: Plataforma (SaaS hobbista) focada em disponibilizar a base pública bruta de CNPJs da Receita Federal para consultas analíticas rápidas via API RESTful e interface visual de Dashboard.
**Hospedagem**: Google Cloud Platform (GCP) Compute Engine - VM `e2-micro` (1 vCPU, 1 GB RAM).

### Stack Tecnológico
- **Ingestão/ETL**: Python (Pandas + DuckDB) para processamento em streaming (chunking).
- **Armazenamento**: Cloudflare R2 (Object Storage S3-compatible).
- **Integração Cloud**: `rclone` (montagem de bucket como unidade local/sincronização).
- **Engine Analítica**: DuckDB (leitura eficiente de Parquets).
- **Backend (API)**: FastAPI com proteção de Rate-Limiting (`slowapi`).
- **Frontend (UI)**: Streamlit.
- **CI/CD e Qualidade**: GitHub Actions, `uv` (gerenciamento de ambiente), `ruff` (linter), `pytest`.

### Estrutura de Dados
- Formato **Apache Parquet** (compressão Snappy).
- Dados organizados no R2 em subpastas por domínio: `cnaes/`, `empresas/`, `estabelecimentos/`, `socios/`, etc.

---

## 2. Progresso Atual

### Infraestrutura e Setup
- [x] Configuração da VPS GCP (`e2-micro`).
- [x] Implementação de IaC via Terraform (`main.tf`).
- [x] Criação do script de Setup Automático Bare-Metal (`scripts/setup_vps.sh`) com `systemd` para auto-restart.
- [x] Padronização do ambiente Python com `uv` e ambiente virtual na VPS.
- [x] Configuração dos serviços Systemd para FastAPI (`buscafri-api.service` na porta 8000) e Streamlit (`buscafri-streamlit.service` na porta 8501).
- [x] Configuração de permissões `NOPASSWD` via `visudo` para deploy automatizado seguro.

### ETL & Conexão Cloud (R2)
- [x] Script de extração e conversão CSV -> Parquet.
- [x] Configuração e testes de conectividade com o Cloudflare R2 (`r2:buscafri-data`).
- [x] Injeção automatizada do arquivo `rclone.conf` via **GitHub Secrets** (`RCLONE_CONF`) diretamente na VPS durante o deploy.

### Backend (API FastAPI) & Frontend (Streamlit)
- [x] Endpoint Health-check e rotas de Busca avançada de CNPJs.
- [x] Refatoração do DuckDB (`app/core/database.py`) para carregamento da extensão `httpfs` e suporte nativo S3/HTTPS para consulta direta no Cloudflare R2.
- [x] Refatoração dos endpoints de busca e exportação (`app/api/v1/endpoints.py`) para consultar diretamente o bucket remoto (`s3://buscafri-data/...`), eliminando a necessidade de baixar os 9GB de dados Parquet para o disco local da VPS `e2-micro`.
- [x] Correção de linter (`Ruff B025` - blocos `except` duplicados).
- [x] Deploy da API e Streamlit operando nas portas 8000 e 8501 da VPS.

### CI/CD e Qualidade (QA)
- [x] Criação e refinamento do Pipeline GitHub Actions (`.github/workflows/deploy.yml`).
- [x] Autenticação via SSH com chaves de deploy e injeção de segredos (`VPS_IP`, `SSH_PRIVATE_KEY`, `RCLONE_CONF`).
- [x] Pipeline 100% automatizado: `git push` valida linters, testes, puxa código na VPS, injeta credenciais do R2, sincroniza dependências com `uv sync` e reinicia os serviços em segundo plano.
- [x] Validação da integridade da suíte de testes de API e ETL (Diagnóstico local em 2025-05-23).

---

## 3. Decisões Técnicas & Otimizações (ADR)
1. **Bare Metal sobre Docker**: Abandonamos a ideia do Docker para o ambiente de produção a fim de preservar o limite restrito de 1GB de RAM da VM `e2-micro`.
2. **Separação Responsável no ETL**: O script de conversão não carrega grandes tabelas na RAM. Pandas é usado apenas para iterar o arquivo em *chunks* e passá-los ao DuckDB para escrita imediata no disco (geração do Parquet).
3. **Leitura Direta Remota (DuckDB S3 via R2)**: Devido ao limite estrito de armazenamento e memória da VM `e2-micro`, o DuckDB foi configurado para consultar os arquivos Parquet diretamente do Cloudflare R2 (`s3://buscafri-data/...`) sob demanda via extensão `httpfs`, eliminando a necessidade de sincronizar ou armazenar os 9GB de dados localmente no servidor.
4. **Exportação Streaming**: As rotas de CSV/XLSX na API não geram arquivos físicos no servidor; utilizam o `StreamingResponse` com buffers em memória para não consumir espaço de disco.
5. **Automação de Deployment**: Toda a alteração na branch `main` executa `ruff`, valida os testes no `pytest` e entra via SSH na VPS apenas se o código estiver íntegro.
6. **Gerenciamento de Dependências**: Migração completa para `uv` com `uv.lock` e `pyproject.toml` para garantir paridade exata entre ambiente local e VPS.

---

## 4. Próxima Sequência Operacional (Backlog Atualizado)
Conforme as diretrizes de governança e o planejamento atual, a prioridade absoluta é a execução das **6 Tasks Operacionais**:
1. **TASK-01**: Validar os dados locais (`NEEDS_VALIDATION` - Estrutura de 28 partições `uf={UF}` e 37 Parquets confirmados; integridade e ordenação pendentes).
2. **TASK-02**: Publicar os arquivos no Cloudflare R2 (Requer inspeção previa, dry-run e plano de recuperação antes do upload).
3. **TASK-03**: Validar o Data Lake remoto.
4. **TASK-04**: Validar os testes de integração.
5. **TASK-05**: **CONCLUÍDO**: Suíte validada localmente (13 testes API + 3 testes ETL aprovados). O registro anterior de 8 testes falhando não foi reproduzido e sua causa permanece inconclusiva.
6. **TASK-06**: Validar CI/CD e publicar as alterações.

*(O backlog detalhado de engenharia e tarefas futuras encontra-se em `.agents/tasks.md`)*

---

## 5. Estado Atual do Projeto

### Ambiente ativo
- Desenvolvimento local está ativo.
- Testes locais estão ativos.
- Cloudflare R2 está disponível como armazenamento de dados.
- FastAPI e DuckDB estão sendo utilizados localmente.
- Os Parquet corrigidos (`data/processed_corrigido/`) e particionados (`data/particionado/estabelecimentos/`) estão disponíveis localmente.

### Produção
- A VPS de produção NÃO está atualmente operacional.
- O ambiente de produção está temporariamente bloqueado.
- A configuração necessária para produção existe/preparada no código (vias variáveis de ambiente), mas não está validada em uma VPS ativa.

### Infraestrutura ainda não implementada
- Nginx/Caddy;
- Domínio;
- DNS;
- SSL/TLS;
- Validação final de firewall;
- Validação de latência API → R2 em ambiente real.

### Dados
- Parquet corrigidos em `data/processed_corrigido/`;
- Tabela `estabelecimentos` particionada por UF em `data/particionado/estabelecimentos/`;
- Estrutura Hive;
- 28 partições identificadas;
- Compressão SNAPPY;
- Tipagem física atual VARCHAR.

### Backend
- FastAPI;
- DuckDB com extensão `httpfs` (S3);
- Rotas principais `/api/v1`;
- Rate limiting implementado.

### Testes
- Suíte atual com 17 testes;
- Status atual: 13 testes de API e 3 testes de ETL validados localmente (Ambiente: Windows, Python 3.13.5, Pytest 9.1.1 em 2025-05-23).
- O teste de integração R2 (`tests/test_r2_connection.py`) não foi executado nesta validação.
- O registro anterior de oito testes de API falhando não foi reproduzido; divergência registrada como inconclusiva.

### Limitações conhecidas
- Cobertura limitada de configuração local/produção;
- Ausência de validação de alta concorrência;
- Dependência dos testes de integração de dados locais;
- Produção ainda não validada contra R2 em uma VPS real.

