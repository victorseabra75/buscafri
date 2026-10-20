# DuckDB e R2

## Conexões DuckDB
1. Inspecione a implementação real do cliente antes de alterá-la.
2. Verifique o ciclo de vida (criação, inicialização, reutilização e encerramento).
3. Não considere uma conexão inicializada apenas porque o objeto foi criado; garanta que ela esteja utilizável.
4. Não mantenha conexões parcialmente inicializadas.
5. Feche recursos com segurança; não feche conexões compartilhadas se outras operações dependerem delas.

## Configuração e Acesso
1. Identifique e valide variáveis de ambiente antes de qualquer operação (`R2_BUCKET_NAME`, etc.).
2. Não use valores padrão silenciosos para configurações críticas.
3. Diferencie: ausência, valor vazio, malformado, credencial inválida ou recurso remoto indisponível.
4. Mantenha consistência entre caminhos locais, destinos rclone e URIs S3.
5. Nunca exponha segredos ou valores de configuração em logs.

## Diagnóstico e Falhas
1. Investigue a causa raiz: extensões httpfs, credenciais, rede, timeouts, permissões ou esquema incompatível.
2. Não presuma que falhas são causadas pelo R2.
3. Diferencie consulta sem resultados, SQL NULL, falha de execução e falha de conexão.
4. **Proibido**: criar fallback silencioso para banco local quando o acesso remoto falhar. Falhas devem ser explícitas.
5. Use timeouts e tentativas limitadas para operações remotas.
