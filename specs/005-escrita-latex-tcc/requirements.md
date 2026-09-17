# Spec 005: Escrita do TCC em LaTeX

**Diretório correspondente:** `latex/tcc_artigo/`
**Skills relacionadas:** abnt-latex, verificacao-citacoes

## Objetivo
Produzir o texto final do TCC em `main.tex` (classe `abntex2[article]`), a partir do conteúdo já desenvolvido e aprovado pelo orientador na fase de proposta.

## Requisitos funcionais
1. Estrutura de seções: Introdução (com delimitação de escopo — ADR-0007), Revisão de Literatura, Objetivos, Metodologia (subseções: construção do dataset, formulação e modelo, blocagem, baselines, pipeline progressivo, reprodutibilidade, caracterização da base), Cronograma (só na proposta — no TCC final vira relato do que foi executado), Resultados, Discussão, Justificativa/Contribuição, Trabalhos Futuros, Conclusão, Referências.
2. Resumo/Abstract seguindo NBR 6028 (150–250 palavras, parágrafo único, sem citação) — na versão final, inclui uma frase de resultado (a proposta não tinha, por ser prospectiva).
3. Referências em `referencias.bib`, formato NBR 6023 via `abntex2cite` — toda entrada passa pela skill `verificacao-citacoes` antes de ser adicionada.
4. Figuras e tabelas são sempre `\input{}`/`\includegraphics{}` de arquivos gerados pela spec 004 — nunca digitadas à mão.
5. Hipótese central, critérios de match/não-match e demais decisões devem refletir os ADRs vigentes — se um ADR mudar, o texto correspondente muda junto.

## Requisitos não funcionais
- Compilação limpa: `make latex DOC=tcc_artigo` sem erros nem citações não resolvidas (`\cite` para chave ausente no `.bib`).
- Marcadores epistêmicos ([HIPÓTESE], [DECISÃO PENDENTE] etc.) podem aparecer como comentários LaTeX (`%`) durante o rascunho, mas são removidos da versão final entregue à banca.

## Critérios de aceite
- [ ] `make latex DOC=tcc_artigo` compila sem erro.
- [ ] Zero entradas em `referencias.bib` sem verificação registrada (ver skill `verificacao-citacoes` para a lista já auditada).
- [ ] Nenhum número em tabela/figura digitado manualmente — todos vêm de `scripts/06_avaliacao_exportacao.py`.
