# Segurança e Operações

## Segredos e Acesso
1. Nunca versione `.env`, credenciais ou artefatos temporários.
2. Nunca coloque segredos em código, YAML, logs ou relatórios.
3. Use GitHub Secrets para gerenciar credenciais.
4. Não imprima valores secretos; informe apenas a presença/ausência.

## Operações Remotas e Infraestrutura
1. Não execute push, deploy ou alteração de infraestrutura sem autorização explícita.
2. Antes de comandos com efeitos colaterais, identifique exatamente o que será alterado e como validar o resultado.
3. Não execute comandos destrutivos apenas para obter um estado inicial.
4. Respeite os limites da VM `e2-micro`.

## Git e Versionamento
1. Inspecione `git status` e preserve alterações do usuário.
2. Revise o diff antes de qualquer ação.
3. Use mensagens convencionais (`feat:`, `fix:`, etc.).
4. Não prometa, nem declare commit/push/deploy concluído sem evidência.
