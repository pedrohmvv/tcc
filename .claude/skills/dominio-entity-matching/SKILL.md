---
name: dominio-entity-matching
description: Conhecimento de domínio de Entity Matching (conceitos, arquiteturas, métricas) aplicado a este projeto. Carrega ao trabalhar em qualquer parte do pipeline de matching, blocagem ou avaliação.
---

# Domínio: Entity Matching

## Conceitos centrais
- **Blocking/candidate generation:** redução do espaço de pares antes do matching. Neste projeto: TF-IDF/BM25 clássico (ADR-0006), não um encoder aprendido.
- **Cross-Encoder:** avalia o par diretamente (concatenado ou não), alta precisão, custo O(n²) na inferência sem blocagem. Arquitetura única deste TCC (ADR-0001).
- **Bi-Encoder:** embeddings independentes por item, comparados por similaridade (cosseno), escalável via ANN. Não implementado neste TCC — trabalho futuro.
- **Hard negatives:** pares negativos semanticamente próximos ao âncora (ex.: mesma marca, produto diferente) — mineração relevante para a spec 003.
- **Data augmentation para EM:** perturbação de tokens (abreviação, troca de unidade, inversão de ordem) — usada só no treino, nunca no teste (ADR-0004).
- **Leakage em EM:** produtos do mesmo agrupamento (aqui: produto canônico) aparecendo em treino e teste. Prevenido por particionamento estratificado por produto canônico, sempre antes de qualquer geração (spec 001).

## Métricas
- Classificação: Precision, Recall, F1 (threshold-dependentes).
- Ranqueamento: MRR, Recall@K, definidos precisamente pós-blocagem (ver skill `avaliacao-baselines`).
- Comparação estatística: McNemar para classificadores pareados sobre o mesmo teste; reportar effect size + IC (ADR-0008).

## Especificidades deste projeto
- Domínio: produtos de supermercado, PT-BR, ruído de sistemas de PDV (abreviação, inversão de tokens, unidades diferentes, marcas regionais, granularidade variável).
- Duas subtarefas: matching entre produtos de lojas distintas (**fatia principal**, nível SKU, ADR-0014) e catálogo-dicionário (**fatia secundária**, categoria e variante). A transitividade vale só para categoria (ADR-0013).
- Regime de recurso: ausência total de ground truth no início — tratado como contribuição metodológica, não limitação a esconder.

## Onde isso já foi decidido
Não redecidir arquitetura, modelo ou estratégia de dados a partir de conhecimento genérico da literatura sem checar `docs/adr/` primeiro. As decisões acima já passaram por análise de trade-off registrada nos ADRs correspondentes.
