# Observabilidade e Logs

## Logging e Métricas
1. Utilize logging estruturado para diagnóstico sem expor segredos, tokens ou senhas.
2. Diferencie erros esperados de erros inesperados.
3. Não utilize logging como substituto do tratamento correto de erros.
4. Evite registrar a mesma exceção repetidamente em múltiplas camadas sem nova informação.

## Diagnóstico e Recursos
1. Diferencie falhas de aplicação, cliente, servidor e dependências externas nas métricas.
2. Respeite estritamente os limites de CPU, RAM e disco do projeto.
3. Não introduza novas dependências ou plataformas de observabilidade sem justificativa clara e necessidade aprovada.
