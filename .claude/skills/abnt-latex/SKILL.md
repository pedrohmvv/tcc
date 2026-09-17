---
name: abnt-latex
description: Convenções de escrita acadêmica ABNT em LaTeX (abnTeX2) para o TCC. Use ao escrever, editar ou revisar qualquer arquivo em latex/tcc_artigo/, incluindo main.tex e referencias.bib.
---

# Escrita ABNT em LaTeX

## Estrutura e classe
- Classe: `abntex2[article]` (seções contínuas, não capítulos).
- Resumo (NBR 6028): 150–250 palavras, parágrafo único, sem citação, seguido de "Palavras-chave:" (3–5 termos, separados por ponto).
- Abstract: mesma estrutura, em inglês, "Keywords:".

## Citações e referências
- Citação autor-data via `abntex2cite` (`\citeonline`, `\cite`, conforme o pacote).
- **Nunca** adicionar uma entrada a `referencias.bib` sem passar pela skill `verificacao-citacoes` primeiro.
- Formato de entrada de evento no `.bib`/texto: nome do evento em maiúsculas, número de edição, ano, local — não fundir o nome do evento com o título dos anais.
- Toda entrada com DOI/acesso eletrônico inclui `\url{}` e nota de acesso — NBR 6023 exige isso para fontes eletrônicas.
- Título da obra referenciada em **negrito** consistente (recurso tipográfico obrigatório pela norma) — ou itálico, mas escolha um e mantenha em todo o documento.

## Figuras e tabelas
- Nunca digitar número de resultado à mão no `.tex`. Toda figura/tabela é gerada por `scripts/06_avaliacao_exportacao.py` e importada via `\input{}`/`\includegraphics{}` a partir de `latex/tcc_artigo/figuras/` ou `/tabelas/`.
- Toda tabela/figura tem fonte creditada ("Fonte: elaborado pelo autor" ou a fonte de dados original).

## Marcadores epistêmicos durante o rascunho
Durante a escrita incremental, marcadores como `[HIPÓTESE]`, `[DECISÃO PENDENTE]`, `[VERIFICAR]` podem aparecer como comentários LaTeX (`% [DECISÃO PENDENTE] ...`) para sinalizar pontos abertos. Removê-los antes da entrega final à banca — eles não fazem parte do texto acadêmico entregável.

## Coerência com ADRs
Antes de escrever a Metodologia, ler `docs/adr/`. O texto deve refletir as decisões vigentes (ex.: Cross-Encoder único — ADR-0001; separação treino/teste — ADR-0004). Se uma decisão mudar, o texto correspondente muda junto — nunca deixar o TCC descrever uma arquitetura ou estratégia que o código não implementa mais.
