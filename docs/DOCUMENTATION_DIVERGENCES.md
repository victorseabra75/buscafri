# Relatório de Divergências Documentais

## 1. Resumo
Este relatório consolida divergências encontradas entre os documentos de governança (`README.md`, `PROJECT_STATUS.md`, `.agents/CONTEXT.md`, `.agents/tasks.md`) do projeto BuscaFri.

## 2. README vs PROJECT_STATUS

| Tema | README afirma | PROJECT_STATUS afirma | Situação |
| :--- | :--- | :--- | :--- |
| **Hospedagem** | GCP `e2-micro` (1 vCPU, 1 GB RAM) | GCP `e2-micro` (1 vCPU, 1 GB RAM) | CONSISTENTE |
| **Stack ETL** | Pandas + DuckDB (streaming) | Python (Pandas + DuckDB) | CONSISTENTE |
| **Arquitetura de Dados** | R2 (S3-compatible) | R2 (S3-compatible) | CONSISTENTE |
| **CI/CD** | Git/GitHub | GitHub Actions + SSH | CONSISTENTE |
| **Infraestrutura** | Nginx / Caddy | Systemd (auto-restart) | DIVERGENTE |

## 3. README vs CONTEXT
*   **README**: Afirma uso de `Nginx` ou `Caddy` como servidor web/proxy.
*   **CONTEXT.md**: Menciona uso de `systemd` para `buscafri-api` e `buscafri-ui` diretamente, sem mencionar explicitamente Nginx/Caddy como proxy.
*   **Divergência**: O uso de proxy reverso não está consolidado entre os documentos.

## 4. PROJECT_STATUS vs CONTEXT
*   **PROJECT_STATUS**: Lista IaC via `Terraform`.
*   **CONTEXT.md**: Não menciona Terraform, focando em `systemd` e `rclone`.
*   **Divergência**: Documentação de IaC está presente apenas no status.

## 5. Conflitos com SOURCE_OF_TRUTH
*   **POTENCIAL DIVERGÊNCIA**: A matriz `SOURCE_OF_TRUTH.md` define `README.md` como fonte primária para documentação, porém, a estrutura de logs de decisão e workflow (`.agents_copy/`) possui informações normativas que, segundo a própria matriz, deveriam estar centralizadas.

## 6. Informações presentes somente em um documento
*   **README.md**: Detalhamento extremo dos fluxos de caso de uso (UC01-UC04).
*   **PROJECT_STATUS.md**: Lista de tickets detalhada (`TICKET-07`) e histórico de decisões técnicas (ADR-001 a 006).
*   **CONTEXT.md**: Definição básica de estrutura de diretórios (`data/raw/`).

## 7. Informações potencialmente desatualizadas
*   **README.md**: Data de atualização marcada como "Março de 2024", enquanto outros logs apontam para operações em 2026.

## 8. Pontos que exigem verificação técnica
*   **Proxy Reverso**: O sistema utiliza Nginx/Caddy ou apenas FastAPI exposto? (AGUARDANDO VERIFICAÇÃO TÉCNICA)
*   **IaC**: O Terraform está efetivamente implementado e em uso? (AGUARDANDO VERIFICAÇÃO TÉCNICA)
*   **Serviços**: A porta 8501 está aberta no firewall conforme o Status indica como pendente? (AGUARDANDO VERIFICAÇÃO TÉCNICA)

## Divergências Confirmadas nas Auditorias 0.5A-D

| Tema | Documentação/Expectativa | Estado técnico confirmado | Classificação |
|---|---|---|---|
| Reverse proxy | README menciona Nginx/Caddy | Não há configuração implementada no repositório atualmente | Divergência |
| Produção VPS | Documentação/status pode pressupor ambiente operacional | VPS atualmente indisponível, portanto determinadas validações permanecem pendentes | Estado desatualizado |
| Tipagem Parquet | Schema lógico prevê DATE/DOUBLE/INTEGER | Existe diferença entre os tipos previstos no schema lógico e os tipos físicos atualmente armazenados, que são VARCHAR | Divergência conhecida |
| Firewall | Liberação de portas de produção mencionada como etapa | Não verificável sem VPS ativa | Não verificado |
| Domínio/HTTPS | Planejamento de publicação | Domínio e SSL/TLS ainda não configurados | Pendente |
| Performance produção | Pode haver expectativa de operação real | Latência API → R2 não validada em VPS real | Não verificado |
| Testes de API Falhando | Histórico afirmava 8 testes falhando na TASK-05 | Execução em 2025-05-23 (`pytest -v tests/test_api*.py tests/test_partitioned_api.py`) resultou em 13 testes aprovados. Causa histórica das 8 falhas permanece inconclusiva | Divergência Histórica Registrada |
