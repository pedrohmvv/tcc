# Scripts do Pipeline — Entity Matching de Produtos de Supermercado

> Pipeline numerado e sequencial: cada script consome a saída do anterior. Executável ponta a
> ponta via `make pipeline` (ver `AGENTS.md` §2 para a regra completa e `CLAUDE.md` para o
> mapeamento canônico e as restrições inegociáveis do TCC).

## Visão geral

```
01_coleta_dados.py ──► 02_analise_exploratoria.py ──► 03_construcao_dataset.py
                                                              │
06_avaliacao_exportacao.py ◄── 05_finetuning.py ◄── 04_baselines.py
```

## Tabela de scripts

| # | Script | Spec | Entrada | Saída |
|---|--------|------|---------|-------|
| 01 | `01_coleta_dados.py` | 001 (RF0) | `dados/brutos/` (imutáveis) | base limpa: `produtos_limpos.parquet`, `dicionario_limpo.parquet`, `relatorio_limpeza.json` em `dados/processados/` (ver `docs/limpeza_dados.md`, ADR-0012) |
| 02 | `02_analise_exploratoria.py` | 001 | base limpa (`dados/processados/`); brutos só para `match_score` | métricas em `resultados/` e tabelas/figuras de EDA em `latex/tcc_artigo/` |
| 03 | `03_construcao_dataset.py` | 001 | base limpa (`dados/processados/`), anotação manual (`docs/protocolo_anotacao.md`) | candidatos e partições em `dados/processados/` (blocagem 1a produto × dicionário feita, config em `configs/blocagem.yaml`; 1b produto × produto pendente) |
| 04 | `04_baselines.py` | 002 | `dados/processados/` | baselines clássicos + LLaMA zero-shot em `resultados/metricas/` |
| 05 | `05_finetuning.py` | 003 | `dados/processados/` | adaptador LoRA do Cross-Encoder em `modelos/` |
| 06 | `06_avaliacao_exportacao.py` | 004 | `dados/processados/`, `modelos/` | métricas, ablação, tabelas/figuras exportadas para `latex/tcc_artigo/` |

Cada spec em `specs/00X-*/requirements.md` detalha os requisitos funcionais e critérios de
aceite do script correspondente. Os ADRs relacionados a cada decisão estão listados no topo de
cada spec.

## Como executar

Pipeline completo:
```bash
make pipeline
```

Scripts individuais (ordem importa — cada um depende da saída do anterior):
```bash
uv run python scripts/01_coleta_dados.py
uv run python scripts/02_analise_exploratoria.py
# ... e assim por diante
```

## Restrições que valem para qualquer script deste pipeline

Ver `CLAUDE.md` para a lista completa; as mais relevantes para quem for editar código aqui:

- Cross-Encoder é a única arquitetura de matching (ADR-0001) — não implementar Bi-Encoder/híbrido.
- Nunca usar o Dataset Generator (Dharma) para gerar ou rotular o conjunto de teste (ADR-0004).
- Treino, validação e teste usam só o texto dos nomes (`description` e `desc_alim`). As colunas
  `codg_item`, `desc_ref` e `match_score` nunca alimentam rótulo, treino, validação, blocagem nem
  anotação (ADR-0010/0011); só os scripts 02, 04 (baseline "ALTA atual", após congelar o teste) e
  06 as leem, direto dos brutos. O 01 as remove ao gravar a base limpa; nada em
  `dados/processados/` pode contê-las (ADR-0011/0012).
- Split por produto canônico sempre **antes** de qualquer geração/aumentação (script 03).
- Seeds fixas e configs versionadas em toda etapa estocástica (skill `reprodutibilidade-ml`).
- Tabelas/figuras de **resultado** em `latex/tcc_artigo/` são geradas pelo script 06, nunca
  editadas à mão (ver `AGENTS.md` §4 para a distinção com tabelas de conteúdo qualitativo).

## Debug

- **`NotImplementedError`:** scripts ainda esqueleto (ver estado de implementação em
  `docs/plano_desenvolvimento.md` §1.0). Implementar seguindo a spec correspondente.
- **`FileNotFoundError`:** execute os scripts na ordem (01 → 06); cada um depende da saída do
  anterior.
- **`ModuleNotFoundError`:** rode `uv sync` (ou `uv sync --extra finetuning` para o script 05).
- **Figuras/tabelas não aparecem no PDF:** confira se o script 06 rodou e recompile com
  `make latex DOC=tcc_artigo`.
