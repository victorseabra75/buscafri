# Tarefa: Consolidar e reorganizar as regras de engenharia do BuscaFri

Quero mesclar as duas versões do `AGENTS.md`, preservando o melhor de ambas: governança concisa, leitura seletiva, roteamento por tarefa e regras técnicas rigorosas para prevenir erros de conexão DuckDB/R2, tratamento incorreto de exceções e problemas de integridade de dados.

## 1. Inspeção antes de modificar

Antes de editar qualquer arquivo:

1. Confirme a raiz do repositório e execute `git status`.
2. Leia o `AGENTS.md` atual integralmente.
3. Inspecione `docs/SOURCE_OF_TRUTH.md`, se existir.
4. Verifique a estrutura real de `docs/`, `docs/engineering/`, `docs/ai-learning/` e a documentação existente.
5. Confirme quais skills citadas estão disponíveis.
6. Identifique regras duplicadas, conflitantes, ausentes ou já documentadas.
7. Preserve todas as alterações preexistentes do usuário.

Não presuma que os arquivos mencionados existem. Não substitua conteúdo sem verificar o estado atual.

## 2. Consolidar o AGENTS.md da raiz

O `AGENTS.md` deve ser o ponto de entrada e governança do projeto, não um manual técnico extenso.

Mantenha aproximadamente 500–900 tokens como meta, sem sacrificar regras essenciais.

Inclua:

- Princípios de engenharia e fluxo obrigatório: Ler → Entender → Investigar → Planejar → Implementar → Testar → Revisar → Documentar.
- Confirmação da raiz, estado do Git e preservação de alterações preexistentes.
- Leitura seletiva dos arquivos e skills pertinentes.
- Consulta às fontes de verdade, especialmente `docs/SOURCE_OF_TRUTH.md`, se existir.
- Proibição de inventar resultados, esconder falhas, enfraquecer testes ou realizar refatorações desnecessárias.
- Proteção de segredos e proibição de operações remotas destrutivas sem autorização explícita.
- Roteamento para os documentos especializados.
- Catálogo de skills existentes e confirmadas, sem presumir disponibilidade.
- Protocolo de entrega com arquivos alterados, causa raiz, testes reais, limitações e riscos.

O `AGENTS.md` deve instruir explicitamente o agente a ler os documentos técnicos pertinentes antes de implementar. Não copie nele todas as regras detalhadas.

## 3. Organizar os documentos especializados

Crie `docs/engineering/` somente se necessário. Reaproveite os arquivos existentes quando forem adequados, evitando duplicação.

Distribua as regras consolidadas nos seguintes documentos:

### `docs/engineering/python-quality.md`

- Python, tipagem, valores opcionais e `None`.
- Ruff e análise estática.
- Tratamento de exceções específicas.
- Uso justificado de `except Exception`.
- Preservação da causa original e proibição de silenciar erros.
- Correção da causa raiz em vez de supressões artificiais.

### `docs/engineering/duckdb-r2.md`

- Inicialização, reutilização e encerramento de conexões DuckDB.
- Falhas de inicialização e estados parcialmente inicializados.
- Diferença entre consulta sem resultados, SQL `NULL` e falha de execução.
- Diagnóstico de extensões, credenciais, endpoint, permissões, rede e timeout.
- Variáveis de ambiente e `.env`.
- Caminhos locais, destinos rclone e URIs S3.
- Tentativas limitadas e prevenção de falsos diagnósticos.
- Proibição de fallback silencioso para dados locais quando a origem remota falhar.
- Proteção de segredos.

### `docs/engineering/data-integrity.md`

- Esquemas, tipos, valores nulos e duplicatas em Parquet.
- Comparações que preservem a multiplicidade dos registros.
- Diferença entre igualdade de contagens e equivalência dos dados.
- Validação antes e depois de publicações.
- ETL, processamento por UF e relatórios de sucesso parcial.
- Streaming e limites de memória.
- Proteção contra perda ou alteração não autorizada de dados.

### `docs/engineering/testing.md`

- Testes unitários, de integração e regressão.
- TDD quando apropriado.
- Mocks para isolar serviços externos nos testes unitários.
- Testes de conexão, configuração, valores nulos e falhas de execução.
- Distinção entre testes aprovados, falhos, ignorados e não executados.
- Testes reais com R2 em ambiente apropriado.
- Proibição de enfraquecer testes ou tratar testes ignorados como aprovação.

### `docs/engineering/security-operations.md`

- `.env`, `.env.example`, GitHub Secrets e proteção de credenciais.
- Logs, permissões e informações sensíveis.
- Git, revisão de diffs e preservação das alterações do usuário.
- CI/CD, SSH, rclone, deploy e publicação.
- Operações destrutivas, remotas ou irreversíveis.
- Autorização explícita e limites da VM `e2-micro`.

### `docs/engineering/observability.md`

- Logs estruturados e métricas.
- Diagnóstico de falhas de requisição, conexão e dependências.
- Prevenção de duplicação de logs.
- Proteção de dados sensíveis.
- Respeito aos limites de CPU, RAM e disco.
- Avaliação de dependências de observabilidade antes de introduzi-las.

### `docs/engineering/audits.md`

Defina um processo de auditoria preventiva com:

1. Inspeção sem efeitos colaterais.
2. Identificação de evidências concretas.
3. Classificação entre defeito comprovado, risco e hipótese.
4. Registro de arquivo, função, causa raiz, impacto e correção proposta.
5. Implementação somente de correções seguras e necessárias.
6. Testes de regressão.
7. Validação com resultados reais.
8. Registro em `docs/ai-learning/` apenas de soluções comprovadas.

Auditorias não autorizam automaticamente uploads, exclusões, migrações em massa, deploy ou outras operações remotas.

## 4. Roteamento no AGENTS.md

Inclua uma tabela compacta de seleção dos documentos:

- Python, tipagem e exceções → `python-quality.md`.
- DuckDB, R2, rclone e conexão → `duckdb-r2.md`.
- ETL, Parquet e integridade → `data-integrity.md` e, quando necessário, `duckdb-r2.md`.
- Testes e regressões → `testing.md`.
- Segurança, Git, CI/CD e operações remotas → `security-operations.md`.
- Logs e métricas → `observability.md`.
- Auditoria preventiva → `audits.md` e os documentos pertinentes ao escopo.

Permita a leitura de múltiplos documentos quando a tarefa envolver várias áreas.

## 5. Regras que não podem ser perdidas

Preserve expressamente as seguintes garantias dos documentos originais:

- Nunca presumir que o diretório atual é a raiz do projeto.
- Usar `pathlib.Path` e verificar caminhos antes de operações.
- Padronizar o nome `R2_BUCKET_NAME`.
- Diferenciar variável ausente, vazia, inválida e recurso indisponível.
- Não criar fallback silencioso de DuckDB remoto para dados locais.
- Não interpretar qualquer falha de rede como objeto remoto inexistente.
- Não considerar a quantidade de linhas suficiente para provar equivalência de Parquet.
- Não marcar uma UF como concluída antes da validação final.
- Não utilizar `except Exception` indiscriminadamente nem silenciar exceções.
- Não tratar teste de integração ignorado como integração aprovada.
- Não expor segredos em código, comandos, logs ou relatórios.
- Não alterar lógica de produção, testes ou infraestrutura durante a reorganização documental.
- Não executar commit ou push sem autorização explícita.
- Não afirmar sucesso sem evidência.

## 6. Compatibilidade e consistência

- Preserve as skills existentes e seus nomes reais.
- Não duplique o conteúdo integral das skills.
- Não altere `docs/SOURCE_OF_TRUTH.md` sem necessidade comprovada.
- Preserve a organização de `docs/ai-learning/`.
- Utilize links relativos válidos.
- Não crie arquivos vazios ou documentos redundantes.
- Se uma regra não tiver localização óbvia, escolha o documento de responsabilidade mais próximo e evite duplicá-la.
- Se houver contradições, resolva-as explicitamente e preserve a regra mais segura compatível com a arquitetura existente.

## 7. Validação de qualidade

Validação de qualidade

Após implementar alterações de código, execute as validações pertinentes ao escopo:

uv run ruff check . --fix — corrigir problemas corrigíveis automaticamente.

uv run ruff format . — aplicar a formatação padronizada.

uv run ruff check . — confirmar que não restam violações do Ruff.

uv run pytest -v — executar a suíte de testes.

Execute os comandos a partir da raiz confirmada do repositório. Antes de comandos que modificam arquivos, verifique git status e preserve alterações preexistentes. Revise o diff após a formatação e correções automáticas.

Se um comando falhar, investigue e corrija a causa quando estiver dentro do escopo autorizado. Não o omita, não enfraqueça testes e não declare a validação concluída sem evidência.

Para alterações exclusivamente documentais, não execute automaticamente ferramentas de formatação de código nem testes da aplicação. Execute as validações documentais pertinentes, incluindo git diff --check, links relativos e revisão integral do diff.

Informe quais comandos foram executados, seus resultados e quaisquer verificações não realizadas.

## 8. Validação final

Execute e informe os resultados reais:

1. Contagem de tokens do novo `AGENTS.md` usando tokenizador compatível, se disponível; caso contrário, identifique a estimativa.
2. Verificação de links relativos.
3. Verificação de duplicações e contradições importantes.
4. `git diff --check`.
5. Revisão integral do diff.
6. Confirmação de que somente os arquivos de documentação previstos foram alterados.
7. Confirmação de que nenhum segredo foi incluído.

Não execute a auditoria do código, testes de produção, operações remotas, commit ou push nesta etapa.

## 9. Entrega

Informe:

- Arquivos criados e modificados.
- Como as regras foram distribuídas.
- Regras preservadas e eventuais decisões de organização.
- Contagem real ou estimada de tokens.
- Resultados das validações.
- Pendências ou limitações.

Pare após concluir a consolidação documental. A auditoria preventiva do código será uma tarefa separada.

**Critério de sucesso:** um `AGENTS.md` curto e eficiente, documentos especializados sem redundância, regras técnicas importantes preservadas e nenhuma alteração no comportamento da aplicação.