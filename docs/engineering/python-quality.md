# Qualidade de Código Python

## Regras Fundamentais
1. Respeite as versões de Python e dependências definidas no `pyproject.toml`.
2. Prefira funções pequenas, com responsabilidades explícitas e interfaces testáveis.
3. Evite duplicação, funções excessivamente complexas e dependências desnecessárias.
4. Mantenha padrões e convenções consistentes com os requisitos do projeto.

## Análise Estática e Tipagem
1. Corrija a causa raiz de alertas do Ruff, Pylance e verificadores de tipo.
2. Não introduza supressões de análise estática (`# type: ignore`, etc.) para ocultar defeitos reais.
3. Não aplique formatação ou correções automáticas a todo o repositório sem avaliar o diff resultante.
4. Modele explicitamente estados opcionais (ex: `T | None`).

## Tratamento de Exceções
1. Capture a exceção mais específica possível.
2. Utilize `except Exception` apenas com justificativa concreta e documentada (ex: fronteira de isolamento).
3. Nunca utilize `except Exception: pass`.
4. Nunca retorne sucesso, dados vazios ou valores padrão para mascarar falhas inesperadas.
5. Preserve a cadeia causal (`raise ... from exc`) ao propagar erros.
6. Se a falha impedir a integridade do resultado, interrompa a operação. Se for seguro continuar (ex: processamento de itens independentes), registre a falha e garanta que o resultado final indique insucesso parcial.
