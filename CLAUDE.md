# CLAUDE.md

> Convenções de engenharia (`uv`, ruff, testes, Makefile): `AGENTS.md`. Este arquivo é o hub do TCC (escopo, ADRs, restrições). Em conflito com artefatos legados do template, este arquivo e as specs prevalecem.

## Projeto

TCC — *Entity Matching em Produtos de Supermercado com Small Language Models Fine-Tuned*. Curso de Ciência de Dados para Negócios, UFPB. Orientador: Prof. Hilton Martins de Brito Ramalho. Execução individual, 16 semanas, dedicação parcial. Vinculado ao projeto CNPq/ALTA (monitoramento de preços em PB/CE/PI) e à infraestrutura da Dharma-AI.

Problema: mapear descrições heterogêneas de produtos (ruído de PDV) a um dicionário canônico (~1.500 entradas), via fine-tuning de um SLM formulado como Cross-Encoder.

**A proposta de TCC aprovada pelo orientador (v3) é a fonte de verdade para objetivos, metodologia e cronograma.** Os `docs/adr/` registram as decisões arquiteturais que saíram dela; os `specs/` detalham a implementação de cada componente. Não reabra uma decisão registrada em ADR sem justificativa explícita e um novo ADR substituindo-o.

## Estrutura do repositório

```
latex/tcc_artigo/        ← ÚNICO formato usado (abntex2[article]); os outros 7 formatos do template foram removidos
  main.tex                  texto do TCC
  referencias.bib           só entradas verificadas (ver skill verificacao-citacoes)
  figuras/, tabelas/         gerados por scripts/02_* (EDA) ou scripts/06_* (resultados); nunca editados à mão — ver AGENTS.md §4

dados/
  brutos/                   dados originais do ALTA (imutáveis)
  processados/              partições treino/val/teste, candidatos, anotações

scripts/                  ← pipeline numerado, roda via `make pipeline`
  01_coleta_dados.py         carrega base ALTA + dicionário canônico
  02_analise_exploratoria.py estatísticas descritivas (spec 001)
  03_construcao_dataset.py   blocagem, candidatos, Dataset Generator (treino), ingestão de anotação manual (teste), split anti-vazamento, augmentation (spec 001)
  04_baselines.py            TF-IDF/BM25/Levenshtein/Jaccard/embeddings genéricos + LLaMA zero-shot (spec 002)
  05_finetuning.py           LoRA do Cross-Encoder (spec 003)
  06_avaliacao_exportacao.py métricas, McNemar, ablação, pipeline progressivo, análise de erro; exporta para latex/ (spec 004)

docs/
  adr/                      decisões arquiteturais (Nygard: Contexto/Decisão/Consequências)
  protocolo_anotacao.md     regras de match/não-match (já escrito, ver Seção 4.1 da proposta)
  guia_escrita_cientifica.md, diario_pesquisa.md, anotacao_experimento.md,
  reuniao_orientacao.md, planejamento_sprint.md, checklist_defesa.md  (templates do repo-modelo)

specs/                    ← requisitos + design por componente, antes de implementar
.claude/skills/           ← skills do projeto (Claude Code e Cursor as descobrem)
.cursor/rules/            ← rules do Cursor, condicionais por glob; apontam para skills/specs, sem duplicar
```

`[PREMISSA]` O mapeamento dos scripts 01–06 acima é uma proposta de adaptação do template genérico ao pipeline de EM — ajuste se preferir outra divisão, mas mantenha a ordem (cada script consome a saída do anterior).

## Restrições inegociáveis

- **LaTeX é a única saída de texto do TCC.** Nunca gerar `.docx` ou outro formato para o texto final — isso ficou em Claude.ai como fase de proposta, já encerrada.
- **Cross-Encoder é a única arquitetura de matching neste TCC** (ADR-0001). Bi-Encoder e híbrido são trabalho futuro — não implementar, mesmo que pareça "melhorar" um resultado.
- **Nunca usar o Dataset Generator (Dharma) para gerar ou rotular o conjunto de teste** (ADR-0004). Ele serve só ao treino. Violar isso invalida a avaliação inteira do TCC.
- **Nunca adicionar entrada a `referencias.bib` sem verificação em fonte primária** (skill `verificacao-citacoes`). Isso vale mesmo para referências "óbvias" ou lembradas de treinamento.
- **Seeds fixas e configs versionadas em toda etapa estocástica** (skill `reprodutibilidade-ml`) — particionamento, geração, treino.
- **Split por produto canônico antes de qualquer geração/augmentation** — nunca depois. Vazamento entre partições invalida a Seção 4 inteira da proposta.
- **Blocagem é TF-IDF/BM25 clássico, não uma arquitetura aprendida** (ADR-0006). Não confundir com Bi-Encoder.

## Comandos

| Comando | Efeito |
|---|---|
| `make pipeline` | roda scripts 01→06 |
| `make latex DOC=tcc_artigo` | compila o PDF do TCC |
| `make check` | lint + typecheck + testes (mesmo do CI) |
| `make test` | pytest |
| `make typecheck` | mypy |
| `make clean` / `make latex-clean` | limpa caches / auxiliares do LaTeX |

## Antes de implementar algo novo

1. Existe spec em `specs/`? Leia antes de codificar.
2. A decisão já está em `docs/adr/`? Não reabra sem novo ADR.
3. Existe skill relevante em `.claude/skills/`? Ela carrega sozinha quando o contexto casa, mas vale checar a lista se algo parecer estranho.
4. Regra de anotação em dúvida? `docs/protocolo_anotacao.md` é a fonte — nunca inventar critério novo de match/não-match ad-hoc no código.
