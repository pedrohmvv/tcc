# Spec 004: Avaliação final, ablação e análise de erro

**Script correspondente:** `scripts/06_avaliacao_exportacao.py`
**ADRs relacionados:** 0006, 0007, 0008, 0013, 0014

## Objetivo
Consolidar avaliação comparativa, testes estatísticos, ablação, avaliação das duas fatias (produto × produto, principal; produto × dicionário, secundária) e análise de erro qualitativa; exportar todos os artefatos para `latex/tcc_artigo/`.

## Requisitos funcionais
1. Comparação do Cross-Encoder fine-tuned contra os 6 baselines (spec 002), com teste de McNemar + tamanho de efeito + IC (ADR-0008) — não reportar apenas p-valor.
2. Avaliação separada por fatia: a **principal** (produto, produto), com o adaptador produto × produto, e a **secundária** (produto, entrada canônica), com o adaptador produto × dicionário (ADR-0013, ADR-0014). Cada uma é um regime de rótulo próprio (SKU × categoria/variante), com adaptador próprio; nenhuma é demonstração de generalização "sem retreino". A comparação do item 1 vale por adaptador, cada um na sua fatia.
3. Ablação de pelo menos dois fatores: impacto da aumentação sintética; impacto da mineração de negativos difíceis. Fator candidato adicional: com/sem dados da TAIL, só no adaptador produto × produto. Com dois adaptadores a ablação é a primeira a encolher se o prazo apertar.
4. Análise de pipeline progressivo: definir limiar de confiança sobre o baseline lexical mais forte (TF-IDF ou BM25); pares acima do limiar são resolvidos sem o SLM; medir fração de pares resolvida pelo método barato, economia computacional e eventual perda de acurácia. **Reaproveitar as saídas já geradas** (sem novo treinamento).
5. Análise de erro qualitativa: taxonomia de falhas por tipo de ruído (abreviação, unidade, marca, categoria), com exemplos.
6. Exportar todas as tabelas/figuras diretamente para `latex/tcc_artigo/tabelas/` e `latex/tcc_artigo/figuras/` — nunca inserir número manualmente no `.tex`.
7. **Benchmark externo TAIL**, só com o adaptador produto × produto (o da fatia principal): tabela separada, rotulada como exploratória, com McNemar pareado contra as predições salvas da TAIL, bootstrap por cluster (grupos de títulos ligados por positivos), contagens absolutas TP/FP/FN e uma análise de sensibilidade sem os pares que só diferem por sufixo, definida **antes** de ver os resultados.

## Critérios de aceite
- [ ] Tabela comparativa final com McNemar, effect size e IC para cada baseline vs. Cross-Encoder.
- [ ] Recall@K da fatia sem dicionário reportado separadamente da fatia com dicionário.
- [ ] Tabela do benchmark externo TAIL, separada e rotulada como exploratória, com IC por cluster e contagens absolutas.
- [ ] Economia computacional do pipeline progressivo quantificada (% de pares resolvidos sem SLM, tempo/custo poupado).
- [ ] Taxonomia de erro documentada com pelo menos um exemplo real por categoria.
