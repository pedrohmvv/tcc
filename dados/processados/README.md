# Dados Processados

> Gerados pelo pipeline e **regeneráveis**: ficam fora do git (texto derivado do ALTA, abertura ainda não autorizada) e são reproduzidos de forma determinística por `make pipeline`. Nunca editar à mão. Os brutos em `dados/brutos/` são imutáveis.

## Arquivos

| Arquivo | Gerado por | Conteúdo |
|---|---|---|
| `produtos_limpos.parquet` | script 01 (ADR-0012) | Base de trabalho: 29.130 registros após remover duplicatas exatas, com as flags `texto_repetido_na_loja` e `preco_invalido`. **Sem** `codg_item`, `desc_ref`, `match_score` (ADR-0011). |
| `dicionario_limpo.parquet` | script 01 | Dicionário canônico (1.593 entradas) sem as colunas vazias do CSV original. |
| `relatorio_limpeza.json` | script 01 | Contagens de cada critério e SHA-256 dos brutos e do conteúdo limpo, para conferir reprodutibilidade. |
| `candidatos_blocagem.parquet` | script 03 | Candidatos da blocagem produto × dicionário (TF-IDF, k=20, congelados em `configs/blocagem.yaml`; spec 001, tarefa 1.2a). Só `id_produto`, `metodo`, `rank`, `desc_alim`, `score`. O recall por método e k fica em `resultados/metricas/recall_blocagem.csv`. A blocagem produto × produto (1.2b) está pendente. |
| `anotacoes_amostra_cega.csv` | script 03 gera a planilha **vazia**; o autor anota | Amostra cega (50 produtos, seed 42, separador `;`) para medir o recall da blocagem. Sem candidatos. Nunca sobrescrita pelo script; versionada no git (exceção `anotacoes*.csv`). |
| `{treino,validacao,teste}.parquet` | script 03 (pendente) | Partições por produto canônico, sem vazamento (ADR-0004). |
| `anotacoes*.csv` | manual (fora do pipeline) | Padrão-ouro anotado — **única exceção versionada no git** (`.gitignore`), por não ser regenerável. |

Critérios de limpeza e justificativas: `docs/limpeza_dados.md`.
