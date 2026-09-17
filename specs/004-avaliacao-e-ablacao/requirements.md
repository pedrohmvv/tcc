# Spec 004: Avaliação final, ablação e análise de erro

**Script correspondente:** `scripts/06_avaliacao_exportacao.py`
**ADRs relacionados:** 0006, 0007, 0008

## Objetivo
Consolidar avaliação comparativa, testes estatísticos, ablação, validação da subtarefa intra-base e análise de erro qualitativa; exportar todos os artefatos para `latex/tcc_artigo/`.

## Requisitos funcionais
1. Comparação do Cross-Encoder fine-tuned contra os 6 baselines (spec 002), com teste de McNemar + tamanho de efeito + IC (ADR-0008) — não reportar apenas p-valor.
2. Avaliação separada da fatia suplementar (produto, produto) sem dicionário (ADR-0007), demonstrando generalização do mesmo modelo sem retreino.
3. Ablação de pelo menos dois fatores: impacto da aumentação sintética; impacto da mineração de negativos difíceis.
4. Análise de pipeline progressivo: definir limiar de confiança sobre o baseline lexical mais forte (TF-IDF ou BM25); pares acima do limiar são resolvidos sem o SLM; medir fração de pares resolvida pelo método barato, economia computacional e eventual perda de acurácia. **Reaproveitar as saídas já geradas** (sem novo treinamento).
5. Análise de erro qualitativa: taxonomia de falhas por tipo de ruído (abreviação, unidade, marca, categoria), com exemplos.
6. Exportar todas as tabelas/figuras diretamente para `latex/tcc_artigo/tabelas/` e `latex/tcc_artigo/figuras/` — nunca inserir número manualmente no `.tex`.

## Critérios de aceite
- [ ] Tabela comparativa final com McNemar, effect size e IC para cada baseline vs. Cross-Encoder.
- [ ] Recall@K da fatia sem dicionário reportado separadamente da fatia com dicionário.
- [ ] Economia computacional do pipeline progressivo quantificada (% de pares resolvidos sem SLM, tempo/custo poupado).
- [ ] Taxonomia de erro documentada com pelo menos um exemplo real por categoria.
