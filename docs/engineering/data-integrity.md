# Integridade de Dados

## Esquemas e Tipos
1. Inspecione o esquema real antes de assumir tipos ou ordenação.
2. Não converta tipos automaticamente sem validar perda de precisão ou alteração semântica.
3. Não descarte registros, duplicatas ou valores nulos sem regra de negócio documentada.

## Validação e Comparação
1. Igualdade na contagem de linhas não prova equivalência. Se necessário, use comparações que preservem a multiplicidade dos registros.
2. Valide a integridade de arquivos antes e depois de qualquer publicação/upload.
3. Teste casos extremos: dados vazios, filtros opcionais, nulos e valores inesperados.

## Processamento (ETL)
1. Prefira processamento por streaming ou incremental para respeitar limites de memória da VM `e2-micro`.
2. Não introduza materializações completas em memória.
3. Relatórios de ETL devem distinguir itens publicados, atualizados, ignorados, falhos e não processados.
4. Falhas parciais em processamento por UF devem ser registradas individualmente, sem mascarar o resultado total como sucesso.
5. Use consultas parametrizadas (nunca concatene valores fornecidos pelo usuário).
