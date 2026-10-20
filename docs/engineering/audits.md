# Auditorias Preventivas

## Procedimento Padrão
Quando solicitada uma auditoria preventiva, siga estritamente as fases abaixo:

### Fase A — Inspeção Sem Efeitos Colaterais
1. Inspecione o repositório (`pyproject.toml`, testes, scripts de ETL/migração, config DuckDB/R2, workflows).
2. **Proibido**: Executar uploads, exclusões, migrações em massa ou operações destrutivas.

### Fase B — Classificação das Ocorrências
Investigue ocorrências concretas de:
- Variáveis sem definição ou não validadas.
- Caminhos dependentes do diretório de execução atual.
- Inconsistências entre caminhos locais, rclone e S3.
- Falhas de tratamento de erros ou valores nulos.
- Falta de testes de regressão.

Para cada item, reporte: arquivo, função, evidência, causa raiz, impacto, classificação (defeito comprovado, risco ou hipótese), correção proposta, teste necessário e risco da alteração.

### Fase C — Correções
1. Implemente apenas correções seguras e necessárias, acompanhadas de testes de regressão.
2. Solicite autorização antes de alterações arquiteturais ou operacionais complexas.

### Fase D — Validação
Execute as verificações configuradas no projeto e documente comandos e resultados reais.

### Fase E — Aprendizado
Atualize `docs/ai-learning/` apenas com causas raiz e soluções comprovadas.

*Nota: Uma auditoria preventiva não autoriza automaticamente nenhuma operação remota (upload, deploy, exclusão).*
