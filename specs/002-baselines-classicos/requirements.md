# Spec 002: Baselines clássicos e zero-shot

**Script correspondente:** `scripts/04_baselines.py`
**ADRs relacionados:** 0002, 0006, 0008, 0011

## Objetivo
Estabelecer o piso de comparação obrigatório antes de qualquer modelo especializado, com protocolo de avaliação congelado e reutilizado por todos os métodos subsequentes.

## Requisitos funcionais
1. Implementar TF-IDF, BM25, Levenshtein, Jaccard e um método de embeddings genéricos (sem fine-tuning) para o mesmo conjunto de teste.
2. Implementar avaliação zero-shot do LLaMA 3.2 3B (mesmo checkpoint-base que será fine-tuned na spec 003) via prompt estruturado para decisão match/não-match — não usar um modelo diferente para este baseline (ver ADR-0002 e ADR-0008: isola o efeito da especialização).
3. Usar a mesma blocagem (spec 001 / ADR-0006) para gerar candidatos antes de aplicar qualquer baseline de ranqueamento.
4. Implementar o baseline "ALTA atual" (ADR-0011): `desc_ref`/`codg_item` como predição de entrada canônica e `match_score` como score de confiança, lidos direto dos brutos **somente após o congelamento do teste**, avaliados no mesmo harness. Vale só para a fatia produto × canônico. Reportar duas versões — condicionada aos registros com predição e sobre o total (sem predição = falha) — sem escolher a favorável depois.

## Requisitos não funcionais
- Harness de avaliação único e congelado: a spec 003/004 deve reutilizar exatamente o mesmo código de cálculo de métricas, não reimplementar.
- Métricas obrigatórias: Precision, Recall, F1 (decisão binária); MRR, Recall@K (ranqueamento pós-blocagem).

## Critérios de aceite
- [ ] Tabela comparativa reprodutível (mesmo seed, mesmo conjunto de teste) para os 7 métodos (5 clássicos + zero-shot + ALTA atual na fatia produto × canônico).
- [ ] Recall@K reportado junto ao recall da blocagem isolada (spec 001), para diferenciar erro de blocagem de erro de ranqueamento.
