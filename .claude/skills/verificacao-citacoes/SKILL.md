---
name: verificacao-citacoes
description: Regra anti-alucinação para referências bibliográficas do TCC. Use SEMPRE antes de adicionar uma entrada a referencias.bib ou citar um trabalho no texto do TCC.
---

# Verificação de citações

## Regra inegociável
Nunca adicionar uma entrada a `referencias.bib` ou citar um autor/ano no texto sem verificar, em fonte primária (DBLP, ACL Anthology, ACM DL, VLDB Endowment, arXiv, página do venue), os seguintes campos: autor(es) completos, ano, título exato, venue, páginas, DOI quando existir. Referência lembrada de treinamento sem essa verificação é tratada como possível alucinação, não como fato.

## Fluxo
1. Buscar a referência (web search) antes de escrever a citação.
2. Confirmar autor/ano/venue/páginas em pelo menos uma fonte primária.
3. Se não for possível confirmar, marcar `[VERIFICAR]` no rascunho e não incluir no `.bib` até resolver.
4. Nunca inventar página, DOI ou venue para "completar" uma entrada incompleta.

## Referências já auditadas nesta fase do projeto (reuso direto, sem nova verificação)
Brunner & Stockinger (2020, EDBT); Kasai et al. (2019, ACL); Konda et al. (2016, PVLDB, Magellan); Li et al. (2020, PVLDB, Ditto); Mudgal et al. (2018, SIGMOD, DeepMatcher); Peeters & Bizer (2021, PVLDB); Peeters & Bizer (2022, WWW Companion); Peeters & Bizer (2023, ADBIS); Peeters, Der & Bizer (2024, EDBT, WDC Products); Reimers & Gurevych (2019, EMNLP-IJCNLP, Sentence-BERT); Silva et al. (2021, BRACIS); Steiner, Peeters & Bizer (2025, ICDEW); Thirumuruganathan et al. (2021, PVLDB); Tu et al. (2022, SIGMOD); Wang, Li & Wang (2023, ICDE, Sudowoodo). Dados completos em `latex/tcc_artigo/referencias.bib` uma vez migrados do documento de proposta.

## Por que isso importa mais aqui
O TCC já teve um parecer do orientador apontando concentração excessiva de fontes de um único grupo de pesquisa — a diversidade de fontes já foi corrigida uma vez; não reintroduzir o viés adicionando só referências de conveniência sem checar.
