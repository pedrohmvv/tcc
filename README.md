# Entity Matching em Produtos de Supermercado com Small Language Models Fine-Tuned

> TCC — Ciência de Dados para Negócios, UFPB. Orientador: Prof. Hilton Martins de Brito Ramalho.

Trabalho de Conclusão de Curso que investiga o uso de *fine-tuning* de um Small Language Model (SLM), formulado como Cross-Encoder, para mapear descrições heterogêneas de produtos de supermercado (com ruído típico de PDV) a um dicionário canônico de ~1.500 entradas.

O trabalho está vinculado ao projeto **CNPq/ALTA** (monitoramento de preços em PB/CE/PI) — fonte dos dados reais — e usa a infraestrutura de fine-tuning da **Dharma-AI**.

**A proposta de TCC aprovada pelo orientador (v3) é a fonte de verdade** para objetivos, metodologia e cronograma. Este repositório implementa essa proposta; as decisões que derivam dela estão registradas como ADRs, e a implementação de cada componente está detalhada em specs antes do código.

---

## O problema

Bases de precificação como a do ALTA trazem descrições de produto diretamente do PDV das lojas — abreviadas, com ruído tipográfico, ordens de token diferentes ("OLEO SOJA LIZA 900ML" vs. "OLEO COMP SOJA LIZA 0,9L"). Para agregar preços do mesmo produto entre lojas e ao longo do tempo, cada descrição bruta precisa ser mapeada a uma entrada de um dicionário canônico (~1.500 produtos).

Este TCC avalia se um SLM fine-tuned, formulado como Cross-Encoder (classificação binária de pares produto × entrada canônica), supera baselines clássicos (TF-IDF, BM25, Levenshtein, Jaccard, embeddings genéricos) e o mesmo modelo em zero-shot.

---

## Decisões arquiteturais (ADRs)

Decisões não devem ser reabertas sem um novo ADR substituindo o anterior. Ver `docs/adr/` para o texto completo (contexto, decisão, consequências).

| ADR | Decisão |
|---|---|
| [0001](docs/adr/0001-formulacao-cross-encoder.md) | Cross-Encoder é a única arquitetura de matching — Bi-Encoder e híbrido ficam como trabalho futuro |
| [0002](docs/adr/0002-modelo-llama-3-2-3b.md) | LLaMA 3.2 3B como SLM principal (Gemma 2 2B como fallback) |
| [0003](docs/adr/0003-lora-bf16-sem-quantizacao.md) | LoRA em bf16, sem quantização de 4 bits |
| [0004](docs/adr/0004-estrategia-ground-truth-treino-teste.md) | **Crítico:** treino via Dataset Generator (Dharma), teste 100% anotado manualmente e independente do Generator |
| [0005](docs/adr/0005-confiabilidade-teste-reteste.md) | Confiabilidade via teste-reteste intra-anotador (Kappa ≥ 0,75), não Kappa inter-anotador |
| [0006](docs/adr/0006-blocagem-classica-tfidf-bm25.md) | Blocagem via TF-IDF/BM25 clássico, não uma arquitetura aprendida |
| [0007](docs/adr/0007-escopo-catalogo-dicionario.md) | Escopo fechado na subtarefa catálogo-dicionário; matching intra-base é consequência transitiva |
| [0008](docs/adr/0008-teste-estatistico-mcnemar.md) | Significância via teste de McNemar + tamanho de efeito, sem superdimensionar a hipótese |
| [0009](docs/adr/0009-contingencia-computacional.md) | Plano de contingência computacional (nuvem acadêmica / Colab Pro / fallback Gemma 2 2B) |

As duas restrições mais rígidas do projeto são o **ADR-0001** (nunca implementar Bi-Encoder/híbrido) e o **ADR-0004** (nunca usar o Dataset Generator para gerar ou rotular o conjunto de teste — isso invalidaria a avaliação inteira).

---

## Estrutura do repositório

```
latex/tcc_artigo/        ← formato final do TCC (abntex2[article])
  main.tex                  texto do TCC
  referencias.bib           só entradas verificadas (skill verificacao-citacoes)
  figuras/, tabelas/         gerados pelo pipeline, nunca editados à mão

dados/
  brutos/                   dados originais do ALTA (imutáveis)
  processados/              partições treino/val/teste, candidatos, anotações

scripts/                  ← pipeline numerado, roda via `make pipeline`
  01_coleta_dados.py          carrega base ALTA + dicionário canônico
  02_analise_exploratoria.py  estatísticas descritivas (spec 001)
  03 → 06                     construção do dataset, baselines, fine-tuning, avaliação
                               (ver "Estado atual" abaixo — nomes ainda em transição)

docs/
  adr/                      decisões arquiteturais (Nygard: Contexto/Decisão/Consequências)
  protocolo_anotacao.md     regras de match/não-match para a anotação manual do teste

specs/                    ← requisitos + design por componente, escritos antes do código
.claude/skills/           ← convenções carregadas automaticamente pelo Claude Code
```

---

## Pipeline (specs)

Cada etapa tem uma spec própria em `specs/`, com objetivo e ADRs relacionados:

| Script | Spec | Objetivo |
|---|---|---|
| `01_coleta_dados.py` | — | Carrega base ALTA + dicionário canônico |
| `02_analise_exploratoria.py` | [001](specs/001-construcao-dataset-ground-truth/requirements.md) | Estatísticas descritivas |
| `03_construcao_dataset.py` | [001](specs/001-construcao-dataset-ground-truth/requirements.md) | Blocagem, candidatos, geração assistida (treino), ingestão de anotação manual (teste), split sem vazamento |
| `04_baselines.py` | [002](specs/002-baselines-classicos/requirements.md) | TF-IDF/BM25/Levenshtein/Jaccard/embeddings genéricos + LLaMA zero-shot |
| `05_finetuning.py` | [003](specs/003-finetuning-cross-encoder/requirements.md) | LoRA do Cross-Encoder |
| `06_avaliacao_exportacao.py` | [004](specs/004-avaliacao-e-ablacao/requirements.md) | Métricas, McNemar, ablação, análise de erro; exporta para `latex/tcc_artigo/` |
| `latex/tcc_artigo/main.tex` | [005](specs/005-escrita-latex-tcc/requirements.md) | Texto final do TCC |

A anotação manual do conjunto de teste segue as regras de `docs/protocolo_anotacao.md` — nunca inventar critério de match/não-match ad-hoc no código.

---

## Comandos

| Comando | Efeito |
|---|---|
| `make setup` | instala dependências com `uv` |
| `make pipeline` | roda os scripts 01→06 |
| `make latex DOC=tcc_artigo` | compila o PDF do TCC |
| `make check` | lint + typecheck + testes (mesmo do CI) |
| `make test` | pytest |
| `make typecheck` | mypy |
| `make clean` / `make latex-clean` | limpa caches / auxiliares do LaTeX |

Requisitos: Python 3.14+ (via `uv`), `make`, e uma distribuição LaTeX (`mactex`/`texlive-full`/MiKTeX) para compilar o PDF.

---

## Restrições inegociáveis

Resumo — a versão completa está em [CLAUDE.md](CLAUDE.md):

- LaTeX (`latex/tcc_artigo/`) é a única saída de texto do TCC.
- Cross-Encoder é a única arquitetura de matching (ADR-0001).
- O Dataset Generator (Dharma) nunca gera ou rotula o conjunto de teste (ADR-0004).
- Nenhuma entrada entra em `referencias.bib` sem verificação em fonte primária (skill `verificacao-citacoes`).
- Seeds fixas e configs versionadas em toda etapa estocástica (skill `reprodutibilidade-ml`).
- Split por produto canônico acontece antes de qualquer geração/augmentation.
- Blocagem é TF-IDF/BM25 clássico, não uma arquitetura aprendida (ADR-0006).

---

## Estado atual

Este repositório nasceu do template genérico `lema-ufpb/modelo-academico` e está em processo de adaptação ao escopo real do TCC (ver `README-INTEGRACAO.md` para o histórico da integração). Pendências conhecidas:

- Os scripts em `scripts/` e os alvos do `Makefile` ainda usam a nomenclatura genérica do template (`03_preprocessamento.py`, `04_treinamento_modelo.py`, ...); o mapeamento para os nomes referenciados pelas specs (`03_construcao_dataset.py`, `04_baselines.py`, `05_finetuning.py`, `06_avaliacao_exportacao.py`) ainda não foi aplicado.
- `latex/` ainda contém os 8 formatos do template; só `tcc_artigo/` é usado neste TCC — os outros 7 devem ser removidos.
- `[DECISÃO PENDENTE]` granularidade do dicionário canônico (afeta spec 001 e o protocolo de anotação).
- `[a confirmar]` VRAM de produção vs. config de teste com o time de plataforma da Dharma-AI (ADR-0003).
- `[a confirmar]` autorização de disponibilização do conjunto de teste anotado com a coordenação do projeto ALTA/CNPq.
- Migração do conteúdo já escrito e aprovado pelo orientador (hoje em `.docx`) para `latex/tcc_artigo/main.tex` (spec 005).
