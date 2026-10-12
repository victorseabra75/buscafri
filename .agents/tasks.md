
# BuscaFri --- Backlog de Tarefas e Plano de Desenvolvimento

Este arquivo é a **Fonte Primária de Tarefas** do projeto BuscaFri (conforme `docs/SOURCE_OF_TRUTH.md`).

---

## 📌 Sequência Operacional Prioritária (Atual)

A prioridade atual é **concluir a publicação e validação dos dados no Cloudflare R2 e estabilizar o pipeline de testes do GitHub Actions**.

---

## 🚀 Tasks Operacionais Prioritárias

### TASK-01 — Validar os dados locais
- **Status**: NEEDS_VALIDATION
- **Prioridade**: Alta (P0)
- **Dependências**: Nenhuma
- **Objetivo**: Confirmar que os arquivos Parquet corrigidos e particionados estão prontos para publicação no R2.
- **Atividades**:
  - Identificar diretórios de origem e destino (`data/processed_corrigido/` e `data/particionado/estabelecimentos/`).
  - Validar as 28 partições por UF (`uf=AC` a `uf=TO`, incluindo `uf=EX`), confirmando a estrutura observada: `data/particionado/estabelecimentos/uf={UF}/data_0.parquet`.
  - Verificar nomes, schemas (física VARCHAR observada), contagens de linhas e integridade física.
  - **Comparação**: Se viável, comparar contagens de registros entre arquivos corrigidos e partições UF para garantir integridade.
  - Conferir se a estrutura física corresponde aos caminhos esperados pela aplicação.
  - Registrar total de arquivos e contagens verificadas sem regenerar dados sem necessidade.
- **Critério de Conclusão**: Evidência documentada de que os arquivos locais estão íntegros, consistentes e prontos para upload. Nota: a coluna `uf` pode ser inferida pelo caminho Hive (`uf={UF}`) nas partições, o que explica sua ausência física no schema destas.

---

### TASK-02 — Publicar os arquivos no Cloudflare R2
- **Status**: TODO
- **Prioridade**: Alta (P0)
- **Dependências**: TASK-01
- **Objetivo**: Disponibilizar no bucket `buscafri-data` os dados que serão consumidos pela aplicação.
- **Atividades**:
  - Confirmar a configuração de acesso e credenciais do Cloudflare R2.
  - Inspecionar previamente a estrutura do destino remoto e definir o plano de sincronização.
  - Executar simulação (*dry-run*) antes do envio definitivo quando a ferramenta (ex: `rclone`) oferecer suporte.
  - Verificar caminhos remotos esperados pela aplicação (`estabelecimentos/`, `empresas/`, etc.).
  - Fazer upload dos arquivos corrigidos e particionados preservando arquivos válidos e evitando sobrescritas destrutivas.
  - Definir plano de recuperação para o caso de interrupção ou falha na publicação.
  - Realizar validação pós-upload (conferência de listagem e tamanhos remotos).
  - Garantir que nenhum token, chave ou arquivo de credenciais seja exposto.
- **Critério de Conclusão**: Arquivos disponíveis no R2 nos caminhos esperados, com evidências verificáveis da publicação, sem autorização automática para envio sem os passos de validação prévia.

---

### TASK-03 — Validar o Data Lake remoto
- **Status**: TODO
- **Prioridade**: Alta (P0)
- **Dependências**: TASK-02
- **Objetivo**: Comprovar que o DuckDB consegue ler os dados publicados diretamente do R2 via `httpfs`.
- **Atividades**:
  - Conferir a quantidade e estrutura dos arquivos remotos no R2.
  - Validar caminhos das tabelas e das 28 partições de UF.
  - Executar consultas SQL reais de leitura diretamente no R2 usando DuckDB com extensão `httpfs`.
  - Conferir schemas, amostras de registros e contagens.
  - Verificar o funcionamento das tabelas de referência e da tabela `estabelecimentos`.
- **Critério de Conclusão**: Consultas reais ao R2 retornam dados corretos via DuckDB e os caminhos da aplicação estão confirmados.

---

### TASK-04 — Validar os testes de integração
- **Status**: TODO
- **Prioridade**: Alta (P0)
- **Dependências**: TASK-03
- **Arquivo Relevante**: `tests/test_r2_connection.py`
- **Objetivo**: Confirmar que o teste de integração do DuckDB com o Cloudflare R2 verifica o serviço real.
- **Atividades**:
  - Conferir e ajustar a marcação `@pytest.mark.integration`.
  - Verificar o comportamento quando as credenciais do R2 não estão configuradas (skip explícito e documentado).
  - Confirmar que exceções reais de conexão/consulta provocam falha explícita quando o teste roda com credenciais válidas.
  - Garantir que falhas não sejam silenciadas por `except Exception` genéricos.
  - Garantir que o teste não seja confundido com um teste unitário mockado/independente.
- **Critério de Conclusão**: Teste passa quando a integração real funciona, falha explicitamente em erros reais de conexão, e faz skip explícito na ausência de credenciais.

---

### TASK-05 — Diagnosticar e corrigir os oito testes da API
- **Status**: TODO
- **Prioridade**: Alta (P0)
- **Dependências**: TASK-01, TASK-03
- **Arquivo Relevante**: `tests/test_partitioned_api.py`
- **Falhas Observadas no CI**: `test_busca_uf_ba`, `test_busca_uf_sp`, `test_busca_uf_inexistente`, `test_busca_uf_municipio`, `test_busca_uf_cnae`, `test_busca_paginacao`, `test_exportar_csv`, `test_exportar_xlsx` (HTTP 500 em vez de HTTP 200).
- **Atividades**:
  - Obter traceback completo e identificar a exceção raiz por trás dos erros HTTP 500.
  - Investigar caminhos de acesso, variáveis de ambiente, nomes de colunas, filtros, conversões de tipos e configurações do DuckDB.
  - Diferenciar falha de infraestrutura, falha de configuração e defeito no código da API.
  - Reproduzir e confirmar comportamento localmente e no GitHub Actions.
  - **Atenção**: Preservar identificadores textuais e não realizar casts indiscriminados para numérico/data.
  - Corrigir a causa raiz com a menor alteração necessária, preservando as expectativas dos testes.
- **Critério de Conclusão**: Os 8 testes passam no CI e localmente, com causa raiz identificada e correção validada.

---

### TASK-06 — Validar CI/CD e publicar as alterações
- **Status**: TODO
- **Prioridade**: Alta (P0)
- **Dependências**: TASK-04, TASK-05
- **Objetivo**: Validar a suíte completa no GitHub Actions e publicar os commits de ajuste.
- **Atividades**:
  - Executar linter `ruff check .`.
  - Executar testes unitários e comuns (`pytest`).
  - Executar testes de integração separadamente (`pytest -m integration`).
  - Revisar diffs garantindo ausência de segredos ou arquivos temporários.
  - Conferir branch e remote antes de realizar commit e push.
  - Verificar a execução real da pipeline no GitHub Actions e registrar o resultado.
- **Critério de Conclusão**: Pipeline remota no GitHub Actions executada com sucesso e resultado documentado.

---

## 📦 Backlog de Engenharia (Planejado)

As tarefas abaixo representam melhorias de arquitetura e novas funcionalidades. Elas devem ser executadas seguindo a ordem de prioridade e dependências estabelecida.

---

### FUTURE-01 — Particionamento Hive e ordenação física dos Parquets
- **Status**: TODO
- **Prioridade**: Alta (P1)
- **Arquivo Proposto**: `scripts/partition_data.py` (Confirmar se o script real é `scripts/particionar_estabelecimentos.py`)
- **Objetivo**: Produzir arquivos Parquet particionados por UF com ordenação física dos registros para otimizar o Data Lake.
- **Requisitos Planejados**:
  - Usar DuckDB para gerar os Parquets.
  - Limitar memória: `SET max_memory='4GB'`.
  - Particionar pelo campo `"19"` (UF) **somente para o conjunto de estabelecimentos**.
  - Estrutura esperada: `estabelecimentos/19={UF}/*.parquet`.
  - Ordenação interna (Z-Order/Hierárquica): Município (`"20"`), CNAE (`"11"`), CNPJ básico (`"0"`) todos ASC.
  - Configurações: `ROW_GROUP_SIZE 100000`, compressão `SNAPPY`.
  - Validar compatibilidade de schemas e opções de exportação do DuckDB.
  - **Divergência/Aviso**: Não presumir ordenação física ou early termination sem validação real. Evitar reprocessamento se os dados atuais forem suficientes.
- **Critérios de Aceite**: Script executável; Configuração de memória validada; Estrutura Hive correta; Ordenação validada por amostragem.

---

### FUTURE-02 — Configuração DuckDB e acesso ao Cloudflare R2
- **Status**: TODO
- **Prioridade**: Alta (P1)
- **Área Proposta**: `app/core/database.py`
- **Objetivo**: Estabilizar e padronizar a conexão do DuckDB com o R2 via variáveis de ambiente.
- **Requisitos Planejados**:
  - Carregar extensão `httpfs`.
  - Credenciais exclusivas via envs: `R2_ACCOUNT_ID`, `R2_ENDPOINT`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
  - Configurar: `s3_url_style='path'`, `s3_use_ssl='true'` conforme versão do DuckDB.
  - **Zero Secrets**: Proibir credenciais hardcoded em logs, erros ou traces.
- **Critérios de Aceite**: Inicialização validada; Leitura no R2 confirmada; Falhas diagnosticáveis sem vazar secrets.

---

### FUTURE-03 — Busca FastAPI com Keyset Cursor e Pruning
- **Status**: TODO
- **Prioridade**: Alta (P1)
- **Dependências**: FUTURE-01, FUTURE-02
- **Rota Proposta**: `GET /api/v1/busca/empresas` (Confirmar se a rota real é `app/api/v1/endpoints.py`)
- **Objetivo**: Implementar busca performática com pruning de partição e paginação estável.
- **Requisitos Planejados**:
  - **Pruning**: Direcionar busca para `estabelecimentos/19={UF}/*.parquet` validando a UF contra injeção de caminhos.
  - **Paginação Keyset**: `cursor_municipio`, `cursor_cnae`, `cursor_cnpj`. `limit` padrão 20, max 100.
  - **Determinismo**: Não considerar ordenação física garantia de ordem SQL. Manter `ORDER BY` lógico se necessário para estabilidade do cursor.
  - **Segurança**: Consultas parametrizadas (`conn.execute(query, params)`). Investigar `SET statement_timeout='3s'`.
- **Critérios de Aceite**: Validação de parâmetros; Pruning efetivo; Cursor estável; Proteção contra SQL Injection.

---

### FUTURE-04 — Telemetria e Observabilidade
- **Status**: TODO
- **Prioridade**: Média (P2)
- **Arquivo Proposto**: `app/core/telemetry.py`
- **Objetivo**: Implementar logging estruturado JSON Lines para auditoria e performance.
- **Requisitos Planejados**:
  - Middleware FastAPI com Loguru (`enqueue=True`).
  - Destino: `/var/log/buscafri/queries.jsonl` (produção).
  - Campos: timestamp, client_ip (confiável via proxy), endpoint, params, status_code, latency_ms, cache_status.
  - **Logrotate**: Rotação 10MB, retenção 14 dias, compressão.
- **Critérios de Aceite**: Middleware operacional; Logs estruturados sem secrets; Rotação testada.

---

### FUTURE-05 — Segurança de Aplicação e Infraestrutura
- **Status**: TODO
- **Prioridade**: Alta (P1)
- **Objetivo**: Fortalecer o isolamento e proteção dos serviços.
- **Requisitos Planejados**:
  - **Nginx**: Único ponto de entrada. FastAPI em `127.0.0.1:8000`, Streamlit em `127.0.0.1:8501`.
  - **Rate Limiting**: `limit_req_zone` no Nginx (10r/s, burst=20).
  - **Segurança**: CORS restrito; Pydantic em todas as rotas; Tratamento de erros sem stack traces.
  - **WAF**: Planejar regras básicas de proteção de borda (Cloudflare).
- **Critérios de Aceite**: Portas internas não expostas; Rate limiting funcional; Ausência de vazamento de informações em erros.

---

### FUTURE-06 — Deploy e Gestão de Segredos
- **Status**: TODO
- **Prioridade**: Baixa (P3)
- **Objetivo**: Automatizar o deploy seguro na VPS e2-micro.
- **Requisitos Planejados**:
  - **Systemd**: Serviços com `Restart=always`, `MemoryMax=400M` (sujeito a validação de OOM).
  - **Secrets**: `.env` na VPS com `chmod 600`. Não versionar e não imprimir em logs de CI.
  - **CI/CD**: Pipeline GitHub Actions com verificações obrigatórias antes do deploy.
- **Critérios de Aceite**: Deploy reprodutível via SSH; Serviços saudáveis após atualização; Segredos protegidos.
