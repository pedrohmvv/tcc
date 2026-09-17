# ADR-0005: Confiabilidade via teste-reteste intra-anotador (não Kappa inter-anotador)

**Status:** Aceito

## Contexto
Anotação conduzida por um único anotador (o autor). Cohen's Kappa clássico exige dois anotadores independentes — não calculável neste cenário.

## Decisão
Adotar teste-reteste: pelo menos 50% do conjunto de teste é reanotado após intervalo ≥7 dias, sem acesso aos rótulos originais. Kappa calculado entre as duas passagens mede consistência **intra**-anotador, não concordância entre pessoas. Faixa desejável: Kappa ≥ 0,75.

## Consequências
- Metodologicamente honesto: o texto do TCC declara explicitamente essa limitação, sem forjar uma leitura de Kappa inter-anotador.
- O tamanho do subconjunto de teste-reteste é definido como percentual (≥50%) do conjunto de teste, não um número absoluto fixo — evita a inconsistência apontada no parecer do orientador (300–500 pares de teste vs. 200 de reteste gerava cobertura variável).
- Casos indecidíveis recebem rótulo `incerto` e são adjudicados por consulta ao dicionário canônico oficial, não entrando no conjunto de teste final.

## Alternativas consideradas
- **Segundo anotador parcial** (mesmo que treinado rapidamente): daria Kappa inter-anotador real, mas não está disponível para este TCC. Documentado como melhoria possível se surgir um colaborador disponível.

## Revisão (parecer do avaliador, 2026-08-15)
O parecer da avaliação de TCC I (`docs/parecer/2026-08-15-parecer-avaliador.pdf`) recomendou, como um dos dois pontos de maior peso, envolver um segundo anotador para reduzir o risco de vazamento de critério do treino para os rótulos de teste. Revisitada a alternativa: confirmado que não há colaborador disponível com o perfil necessário (sem acesso ao pipeline de geração) no horizonte deste trabalho. Decisão **reafirmada sem alteração** — teste-reteste permanece como medida de confiabilidade adotada. A limitação é registrada explicitamente em `main.tex`, §4.1 ("Confiabilidade da anotação").
