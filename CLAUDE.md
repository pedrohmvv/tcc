# CLAUDE.md

> Convenções de engenharia (`uv`, ruff, testes, Makefile): `AGENTS.md`. Este arquivo é o hub do TCC (escopo, ADRs, restrições). Em conflito com artefatos legados do template, este arquivo e as specs prevalecem.

## Projeto

TCC — *Entity Matching em Produtos de Supermercado com Small Language Models Fine-Tuned*. Curso de Ciência de Dados para Negócios, UFPB. Orientador: Prof. Hilton Martins de Brito Ramalho. Execução individual, 16 semanas, dedicação parcial. Vinculado ao projeto CNPq/ALTA (monitoramento de preços em PB/CE/PI) e à infraestrutura da Dharma-AI.

Problema: decidir se duas descrições heterogêneas de produtos (ruído de PDV) são o mesmo SKU (**fatia principal, produto × produto**, ADR-0014) e mapear produtos a um dicionário canônico (~1.500 entradas; **fatia secundária**), via fine-tuning de um SLM formulado como Cross-Encoder, com um adaptador LoRA por tipo de par.

**A proposta de TCC aprovada pelo orientador (v3) é a fonte de verdade para objetivos, metodologia e cronograma.** Os `docs/adr/` registram as decisões arquiteturais que saíram dela; os `specs/` detalham a implementação de cada componente. Não reabra uma decisão registrada em ADR sem justificativa explícita e um novo ADR substituindo-o. **Exceção registrada:** o ADR-0014 (decisão do autor, 2026-10-31) inverte a prioridade das fatias em relação à proposta v3; até o `main.tex` ser atualizado (tarefa 5.3 do plano), vale o ADR.

## Estrutura do repositório

```
latex/tcc_artigo/        ← ÚNICO formato usado (abntex2[article]); os outros 7 formatos do template foram removidos
  main.tex                  texto do TCC
  referencias.bib           só entradas verificadas (ver skill verificacao-citacoes)
  figuras/, tabelas/         gerados por scripts/02_* (EDA), scripts/03_* (recall da blocagem) ou scripts/06_* (resultados); nunca editados à mão — ver AGENTS.md §4

dados/
  brutos/                   dados originais do ALTA (imutáveis)
  processados/              base limpa (script 01), partições treino/val/teste, candidatos, anotações

configs/                  ← YAML versionados (`blocagem.yaml`: seed, varredura de k, método e k congelados)

scripts/                  ← pipeline numerado, roda via `make pipeline`
  01_coleta_dados.py         valida os brutos do ALTA e grava a base limpa em dados/processados/ (ADR-0012)
  02_analise_exploratoria.py EDA sobre a base limpa → métricas + tabelas/figuras de EDA (spec 001)
  03_construcao_dataset.py   blocagem (1a produto × dicionário feita; 1b produto × produto pendente), candidatos, Dataset Generator (treino), ingestão de anotação manual (teste), split anti-vazamento, augmentation (spec 001)
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
- **Nunca usar o Dataset Generator (Dharma), nem qualquer outro gerador ou LLM (inclusive o `attack_augmentation` da TAIL e LLM-as-judge), para gerar ou rotular o conjunto de teste ou de validação** (ADR-0004, emendado pelo ADR-0013). Violar isso invalida a avaliação inteira do TCC. O Dataset Generator está suspenso (D-5).
- **Duas regras de match por tipo de par** (ADR-0013): produto × dicionário decide categoria e variante; produto × produto decide SKU (marca e tamanho). Dois adaptadores LoRA, um por tipo de par. **Produto × produto é a fatia e o teste principais; produto × dicionário é a fatia secundária** (ADR-0014).
- **Nada da TAIL é versionado, redistribuído ou publicado sem autorização escrita** (ADR-0013). `invoice-data-normalizer/` está no `.gitignore`.
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
