# Tasks da 1.2b: blocagem produto × produto

**Design:** `design-1b.md` · **Spec:** `requirements.md`, RF1 "1b" · **Branch:** `feat/blocagem-produto-x-produto`
**Status:** T0 a T12 implementadas e verificadas em 2026-11-13; falta só a T13 (sincronização de documentos que dependem do autor). **T10c (reteste) implementada em 2026-11-16** (RED → GREEN, 49 testes); a primeira passada do teste foi concluída pelo autor em 2026-11-16 (último timestamp 11:30:50-03:00), então o reteste só pode ser anotado a partir de 2026-11-23.

## Progresso

Concluídas (GREEN, `make check` verde, nada commitado): **T0, T1, T2, T3, T4, T5a, T5b** (a T5b foi do RED ao GREEN no mesmo passo, a pedido do autor). **T6, T7** (do RED ao GREEN direto, a pedido do autor; T7 sem o IC por bootstrap, que depende do Q10). **T8** (inclui `ids_ancoras` em `ranquear_entre_lojas` e o manifesto `ancoras_lote_NN.csv`; `main()` ainda não chama a 1b, isso é a T12). **T11 e T12** concluídas em 2026-11-13 (`gerar_particao_pxp` e `gerar_conjuntos_pxp` rodaram na base real e reproduziram a medição; `main()` roda a 1a e a 1b; CA-1b-01 a 07 marcados na spec com evidência, salvo a parte produto × dicionário do CA-1b-05). **T9, T10 e T10b** concluídas em 2026-11-13 (a T10b do RED ao GREEN: as 26 funções de transformação, 5 de integração e 3 de contrato do HTML; o reteste ≥ 150 pares, com ≥ 7 dias de intervalo, fica para depois da primeira passada). **Próximo passo é do autor:** o checkpoint (gerar o lote 1 real, anotar, seguir a regra de parada, congelar método e k). Desvio do Design na T5a: não há `ancoras_do_lote`; o orquestrador (T8) fatia a permutação por `[n_já_sorteados : n_já_sorteados + tamanho]`, para o último lote poder ser truncado no teto.

## Regras de execução (valem para todas as tasks)

- **TDD (`dharma-tdd`):** cada task começa com testes numa fixture pequena. **Paro depois do RED e só implemento quando o autor tiver visto os testes falhando.** Se preferir, o RED pode ser agrupado (T0 + T1 + T2, por exemplo) para não parar doze vezes.
- **Testes nas três camadas do `AGENTS.md` §3:** unitário puro; transformação em memória com fixtures do `conftest.py`; integração leve em `tmp_path`.
- **Fixture nova** `produtos_entre_lojas_exemplo` em `tests/conftest.py`: ~15 produtos em 3 lojas, com grupos de SKU conhecidos, texto idêntico entre lojas, um par de dígito divergente (500G × 1KG) e uma unidade equivalente (900ML × 0,9L). Os grupos são construídos na fixture; nenhum dado real é usado como rótulo.
- **Gate de cada task:** `make check` verde (ruff, mypy, pytest). **Commit:** só quando o autor pedir, via `dharma-commit`.
- Nenhuma task usa `codg_item`, `desc_ref`, `match_score`, `invoice-data-normalizer/`, o Dataset Generator ou LLM para gerar ou rotular pares.

## Tasks

| # | Entrega | Onde | Depende de | Requisito | Pronto quando |
|---|---|---|---|---|---|
| **T0** [P] | `configs/blocagem_pxp.yaml` + `carregar_config_pxp` | `configs/`, seção 1.2b do 03, `tests/test_unitario_blocagem_pxp.py` | — | RF1 1b, CA-1b-04 | YAML carrega; método fora de {tfidf, bm25}, k fora de `ks` ou só um dos dois nulo levantam `ValueError` |
| **T1** [P] | `deduplicar_por_texto_e_loja` | 03 | — | CA-1b-01 | uma linha por (texto, loja); `id_texto` igual ao `id_produto` da 1a; ids independentes da ordem de entrada |
| **T2** [P] | `tokens_numericos` e `divergencia_numerica` | 03 | — | RF1 1b (estrato) | 900ML = 0,9L não diverge; 500G × 1KG diverge; sem número em um lado não diverge |
| **T3** | `ranquear_entre_lojas` (TF-IDF e BM25) com `_top_k_entre_lojas` | 03 | T1 | CA-1b-01 | nenhum candidato da mesma loja nem o próprio âncora (assert); desempate estável; tempo do BM25 na base inteira medido e anotado |
| **T4** | `ranquear_ngramas`, fora de `_RANQUEADORES` | 03 | T3 | RF1 1b (pool) | gera top-k só para os âncoras; o config rejeita `ngramas` como método oficial |
| **T5a** | `sortear_ancoras` (permutação semeada, lotes por prefixo) e `decidir_proximo_lote` (regra da §5 do Design) | 03 | T1, T0 | RF1 1b, Q2 (resolvida) | mesma seed → mesma ordem; o lote N é prefixo; a regra para no alvo, no teto ou continua, sem usar o recall |
| **T5b** | `montar_pool` e `montar_planilha_pool` | 03 | T3, T4, T5a | CA-1b-02 | união dos três top-100, alfabética, sem método/rank/score/colunas ALTA (assert); lote existente nunca é sobrescrito |
| **T6** | `validar_anotacao_pool` | 03 | T5b | CA-1b-03 | rótulo fora do domínio, id fora do pool e planilha vazia levantam `ValueError`; âncora não concluída é ignorada, não é erro |
| **T7** | `calcular_recall_pxp` + tabela `.tex` | 03 | T6 | CA-1b-03 | recall@k micro e acerto@k por método e k, com contagens à parte; positivo fora do top-100 do método conta como perda; número da tabela vem do CSV |
| **T8** | `executar_blocagem_pxp` (etapas 1 e 2) + teste de integração em `tmp_path` | 03, `tests/test_integracao_pipeline.py` | T5b, T6, T7 | CA-1b-07 | duas execuções com a mesma config dão arquivos idênticos (hash, ou DataFrame igual se o parquet variar); lote anotado gera recall; etapa 1 não reescreve planilha |

### Checkpoint, fora do código: [PEDRO]

Anotar o lote 1 e seguir a regra de parada (Q2) até o alvo ou o teto. Escolher método e k pelo recall, congelar em `configs/blocagem_pxp.yaml` e **só então** seguir para a T9. Com base nas taxas por faixa (T9), decidir faixas, alocação e a prevalência-alvo (Q8) e o tratamento de texto idêntico (Q7).

| # | Entrega | Onde | Depende de | Requisito | Pronto quando |
|---|---|---|---|---|---|
| **T9** | `taxas_positivos_por_faixa` (só imprime/grava as taxas para o autor escolher a alocação) | 03 | T8, checkpoint | RF1 1b (calibração) | calcula só no pool; não toca os pares do teste |
| **T10** | `sortear_pares_teste` | 03 | T2, T9, congelamento, Q7, Q8 | CA-1b-04, CA-1b-05 | com método ou k nulo: falha; 300 pares entre lojas, produto em no máximo um par, `estrato` e `prob_inclusao` por par, ~20% no estrato de dígito divergente; estrato insuficiente levanta `ValueError` |
| **T10b** | `montar_planilha_teste_pxp`, `validar_anotacao_teste_pxp`, `gravar_planilha_teste_pxp`, `gerar_planilha_teste_pxp` e `ferramentas/anotador_teste.html` | 03, `tests/test_transformacao_planilha_teste_pxp.py`, `tests/test_unitario_anotador_teste.py`, `tests/test_integracao_pipeline.py` | T10 | CA-1b-05, protocolo §5 | planilha `anotacoes_teste_pxp.csv` (`;`) com os 300 pares, sem estrato, score nem colunas da ALTA, em ordem embaralhada com seed e independente da entrada; `id_par` estável; rótulo ∈ {match, nao_match, incerto}, vazio = não anotado; nunca sobrescrita; o HTML tem as mesmas colunas e rótulos do script (teste de contrato) |
| **T10c** | `sortear_pares_reteste`, `montar_planilha_reteste_pxp`, `calcular_kappa_reteste`, `verificar_intervalo_reteste`, `gerar_planilha_reteste_pxp`, `gerar_kappa_reteste_pxp`; flags `--reteste` e `--kappa-reteste` do script 03 (o `main()` sem flag nunca gera o reteste); `n_reteste` e `seed_reteste` em `configs/blocagem_pxp.yaml` | 03, `configs/`, `tests/test_transformacao_reteste_pxp.py`, `tests/test_unitario_blocagem_pxp.py`, `tests/test_integracao_pipeline.py` | T10b, primeira passada completa | ADR-0005, protocolo §4 | 150 pares (≥ 50%) sorteados por estrato sem olhar o rótulo (`incerto` entra); planilha `anotacoes_teste_pxp_reteste.csv` cega, em outra ordem e nunca sobrescrita; Kappa de 3 classes e binário por tipo de par em `resultados/metricas/kappa_reteste_pxp.csv`; falha se o intervalo for menor que 7 dias, contado do último timestamp da primeira passada |
| **T11** | `componentes_conexos`, `particionar_componentes`, `verificar_particao_por_componente`, `vazamento_residual`, `resumir_particao` e `gerar_particao_pxp` | 03, `tests/test_{unitario,transformacao}_particao_pxp.py` | T10 (Q9 resolvida em 2026-11-13: sem proporção, τ = 0,7) | CA-1b-06 | componente em duas partições falha por assert; o vazamento residual é calculado e gravado; o maior componente é reportado |
| **T12** | Integração das etapas 3 a 5 em `executar_blocagem_pxp` e `main()`; `montar_validacao_pxp`, `montar_produtos_treino_pxp`, `gerar_conjuntos_pxp` (`validacao_pxp.parquet`, `produtos_treino_pxp.parquet`); docstring do 03, `scripts/README.md`, `dados/processados/README.md` | 03, docs | T10, T11 | CA-1b-01 a CA-1b-07 | `make check` verde; todos os CAs marcados na spec com evidência |
| **T13** [PEDRO decide] | Sincronizar documentos: protocolo §2.2 (como anotar o pool), plano 1.4.3, ADRs/`main.tex` que dizem "a definir" para D-13 e partição, `docs/resultado_blocagem_pxp.md` | docs, `main.tex` | T7, T11 | Q6 | só com o aval do autor para cada arquivo; nunca antes de existir o número a citar |

## Grafo de dependências

```
T0 ─┐
T1 ─┼─ T3 ─ T4 ─┐
T2 ─┘     │      ├─ T5b ─ T6 ─ T7 ─ T8 ──▶ [checkpoint PEDRO] ─ T9 ─ T10 ─ T11 ─ T12 ─ T13
T0,T1 ─ T5a ─────┘
T2 ──────────────────────────────────────────────────────────────────▶ T10
```

## Validação da quebra

- Granularidade: cada task é uma função ou um artefato, com teste co-locado.
- O grafo bate com a coluna "Depende de".
- Camadas de teste: T0, T1, T2, T5a, T6 e T7 são unitárias; T3, T4, T5b, T9 e T10 usam a fixture em memória; T8 e T12 são integração em `tmp_path`.
- Pontos do autor, sem os quais nada avança: o checkpoint (antes da T9), Q7/Q8 (antes da T10), Q9 (antes da T11; resolvida em 2026-11-13).
