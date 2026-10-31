---
name: avaliacao-baselines
description: Harness de avaliação consistente para comparar baselines e o Cross-Encoder fine-tuned. Use ao escrever código de avaliação, calcular métricas, ou reportar resultados comparativos.
---

# Harness de avaliação

## Métricas obrigatórias
- Classificação binária: Precision, Recall, F1.
- Ranqueamento (pós-blocagem): MRR, Recall@K.

## Definições precisas (ADR-0006)
- **Recall@K** = fração de vezes que o match verdadeiro está entre os k candidatos retornados pela blocagem, após o reranqueamento do Cross-Encoder — não é recall da blocagem isolada (reportar esse separadamente, ver spec 001).
- **MRR** = calculado sobre a posição do match verdadeiro na lista reordenada pelo Cross-Encoder.

## Comparação estatística (ADR-0008)
- Usar teste de McNemar para comparar dois classificadores sobre o mesmo conjunto de teste pareado.
- Sempre reportar tamanho de efeito e intervalo de confiança, independentemente do p-valor — com algumas centenas de pares por fatia (tamanhos em aberto, ADR-0014), diferenças pequenas podem não atingir significância sem que isso invalide a direção do efeito.

## Regras de consistência
- Mesmo conjunto de teste, mesma blocagem, mesmo código de métrica para todos os métodos (5 baselines clássicos + LLaMA zero-shot + Cross-Encoder fine-tuned) — nunca reimplementar cálculo de métrica por método.
- A avaliação da fatia principal (produto-produto, ADR-0014) é reportada separadamente da avaliação da fatia secundária com dicionário (produto-canônico, ADR-0007/0013) — não misturar nas mesmas tabelas sem rotular claramente qual é qual. Cada fatia usa o **seu adaptador LoRA** e a **sua regra de match** (categoria/variante em produto-canônico; SKU em produto-produto).
- **Benchmark externo TAIL** (ADR-0013): só produto-produto, tabela separada e rotulada exploratória, **sem blocagem** (os pares já são dados). O limiar do modelo vem da validação do TCC, nunca do benchmark. Reportar TF-IDF "como publicado" e com limiar da validação, além de PR-AUC. McNemar pareado contra as predições salvas da TAIL, bootstrap por cluster e contagens absolutas TP/FP/FN. Antes de qualquer número novo, o *golden test* deve reproduzir os TP/FP/FN publicados. Os LLMs da TAIL são baselines externos adicionais e não substituem o zero-shot do LLaMA 3.2 3B.
- Baseline "modelo genérico" = o mesmo checkpoint-base do LLaMA 3.2 3B usado no fine-tuning, avaliado zero-shot. Nunca substituir por um modelo diferente (ex.: GPT-4o) para esse baseline específico — isso confundiria tamanho do modelo com efeito de especialização.
