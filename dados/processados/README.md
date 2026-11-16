# Dados Processados

> Gerados pelo pipeline e **regeneráveis**: ficam fora do git (texto derivado do ALTA, abertura ainda não autorizada) e são reproduzidos de forma determinística por `make pipeline`. Nunca editar à mão. Os brutos em `dados/brutos/` são imutáveis.

## Arquivos

| Arquivo | Gerado por | Conteúdo |
|---|---|---|
| `produtos_limpos.parquet` | script 01 (ADR-0012) | Base de trabalho: 29.130 registros após remover duplicatas exatas, com as flags `texto_repetido_na_loja` e `preco_invalido`. **Sem** `codg_item`, `desc_ref`, `match_score` (ADR-0011). |
| `dicionario_limpo.parquet` | script 01 | Dicionário canônico (1.593 entradas) sem as colunas vazias do CSV original. |
| `relatorio_limpeza.json` | script 01 | Contagens de cada critério e SHA-256 dos brutos e do conteúdo limpo, para conferir reprodutibilidade. |
| `candidatos_blocagem.parquet` | script 03 | Candidatos da blocagem produto × dicionário (TF-IDF, k=20, congelados em `configs/blocagem.yaml`; spec 001, tarefa 1.2a). Só `id_produto`, `metodo`, `rank`, `desc_alim`, `score`. O recall por método e k fica em `resultados/metricas/recall_blocagem.csv`. A blocagem produto × produto (1.2b) tem arquivos próprios, abaixo. |
| `anotacoes_amostra_cega.csv` | script 03 gera a planilha **vazia**; o autor anota | Amostra cega (50 produtos, seed 42, separador `;`) para medir o recall da blocagem. Sem candidatos. Nunca sobrescrita pelo script; versionada no git (exceção `anotacoes*.csv`). |
| `pool_cego/lote_NN.csv`, `pool_cego/ancoras_lote_NN.csv` | script 03 gera; o autor anota | Pool cego da 1b em lotes de 25 âncoras (spec 001, RF1 "1b"). Vazio em âncora concluída = não-match. Nunca sobrescrito. Fora do git. |
| `pares_teste_pxp.csv` | script 03 | 300 pares do teste produto × produto, sorteados uma única vez, **sem rótulo** (`id_a`, `id_b`, `estrato`, `prob_inclusao`). Fora do git. |
| `anotacoes_teste_pxp.csv` | script 03 gera a planilha **vazia**; o autor anota | Planilha do teste produto × produto (300 pares, separador `;`), sem estrato, score nem método, em ordem embaralhada com seed. Nunca sobrescrita. O nome casa com a exceção `anotacoes*.csv` do `.gitignore`, mas o repositório é público e a autorização do ALTA para abrir o conjunto anotado está pendente: não commitar sem decidir. |
| `componentes_pxp.parquet` | script 03 | Componente conexo (cosseno TF-IDF ≥ 0,7, mais os pares do teste) e partição (`treino`, `validacao`, `teste`) de cada produto do universo p×p (28.921). Cada componente fica inteiro numa partição (CA-1b-06). |
| `validacao_pxp.parquet` | script 03 | Pares do pool com os dois lados na validação, um por par não ordenado, rótulo do autor (`match` ou `nao_match`; `incerto` fora). Hoje 5.906 pares, 25 `match`. |
| `produtos_treino_pxp.parquet` | script 03 | Só os produtos da partição de treino (sem par, sem rótulo): a única entrada permitida para gerar pares de treino (ADR-0004). Hoje 12.656 produtos. |
| `pares_b2_pxp.csv` | script 03 | Pares do treino que o autor anota (opção B2, ADR-0015): lojas diferentes, mesmo tamanho, cosseno TF-IDF ≥ 0,5; 3.974 pares congelados uma única vez (`id_a`, `id_b`, `score`). Só produtos da partição de treino. Fora do git. |
| `anotacoes_treino_b2_pxp.csv` | script 03 gera a planilha **vazia**; o autor anota | Planilha do B2 (cartão por par, mesma estrutura e mesma ferramenta do teste, `origem = treino_b2`), sem score. Nunca sobrescrita. Mesma cautela do `anotacoes_teste_pxp.csv`: o nome casa com `anotacoes*.csv`, mas não commitar sem decidir sobre o repositório público e a autorização do ALTA. |
| `pares_treino_auto_pxp.parquet` | script 03 (`configs/pares_treino_pxp.yaml`) | Parte A dos pares de treino produto × produto (ADR-0015): negativos por tamanho diferente (`neg_tamanho`, entre lojas e da mesma loja, amostrados por faixa de cosseno) e positivos por perturbação do próprio texto (`pos_unidade`, `pos_ordem`, `pos_abreviacao`, `pos_ruido`, lado B sintético `sint_...`). Hoje 14.200 pares: 8.200 negativos e 6.000 positivos. Só produtos da partição de treino. Fora do git. |
| `treino_pxp.parquet` | script 03 (`gerar_treino_pxp`) | Treino produto × produto (ADR-0015): junta a parte A, as anotações B2 do autor (só `match` e `nao_match`; `incerto` e pendentes ficam de fora; entra o que já estiver anotado) e os pares da TAIL (`pares_tail_pxp.parquet`, quando existir). Mesmo formato dos pares de `validacao_pxp.parquet`, com `origem` por fonte. O resumo por origem e rótulo fica em `resultados/metricas/treino_pxp_resumo.csv`. Fora do git. |
| `teste_pxp.parquet` | script 03 (pendente) | O teste anotado, que só sai da ingestão da anotação do autor. |
| `anotacoes*.csv` | manual (fora do pipeline) | Padrão-ouro anotado — **única exceção versionada no git** (`.gitignore`), por não ser regenerável. |

Critérios de limpeza e justificativas: `docs/limpeza_dados.md`.
