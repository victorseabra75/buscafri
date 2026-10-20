# Testes e Regressão

## Metodologia
1. Antes de corrigir um bug, crie um teste que reproduza a falha (se possível).
2. O teste deve falhar antes da correção e passar depois.
3. Todo defeito confirmado gera obrigatoriamente um teste de regressão.

## Execução e Isolamento
1. Isole dependências externas (R2, etc.) com mocks em testes unitários.
2. Separe claramente testes unitários, de integração e verificações manuais.
3. Não dependa de acesso real ao R2 na suíte completa. Testes de integração devem ser executados apenas quando necessário e com credenciais configuradas.
4. Não enfraqueça testes (ex: mocks que mascaram o erro, ignorar testes, etc.) para fazer a suíte passar.
5. Não trate testes ignorados como prova de sucesso.

## Escopo
1. Teste caminhos incorretos, configurações ausentes, nulos e falhas externas.
2. Execute a suíte completa quando a tarefa ou pipeline exigirem.
3. Não declare execução de um teste sem tê-lo rodado efetivamente.
