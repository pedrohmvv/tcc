# Retomada: estado do TCC em 2026-11-16 (substitui `retomada_sessao_2026-11-13.md`)

> **Escrito para:** o autor e para uma sessão nova do Claude Code que comece do zero.
> **Lista viva de pendências do autor:** `docs/pendencias_autor.md`. **Prompt para planejar o harness de avaliação:** `docs/prompt_planejamento_harness.md`.
> O documento de 13/11 continua útil como referência (mapa do código, números de base, armadilhas), mas **não conhece** o reteste, a adjudicação, o teste final nem a TAIL. Em divergência, vale este.

## 1. Estado em 10 linhas

- **Pronto e verde (982 testes, `make check`):** scripts 01 e 02; blocagem 1a e 1b; partição por componente; pares de treino (parte A, B2 pronta para anotar, **TAIL**); **teste final** `teste_pxp.parquet`; reteste; adjudicação.
- **Teste final produto × produto:** 290 pares (142 `match`, 148 `nao_match`), `prob_inclusao` e `estrato` por par, fonte do rótulo registrada. Os 10 `incerto` ficaram fora.
- **Treino:** `treino_pxp.parquet` com 37.958 pares = 14.200 (parte A) + 23.758 (TAIL) + 0 (B2, ainda sem anotação do autor).
- **Validação:** `validacao_pxp.parquet`, 5.906 pares (25 `match`).
- **Esqueleto:** scripts 04, 05 e 06 (`NotImplementedError`), `modelos/` vazio. **Nenhuma métrica de modelo ou baseline existe ainda.**
- **Fatia produto × dicionário:** blocagem 1a pronta; teste de 100 pares, treino e RF6 pendentes (D-5 suspenso).
- **Nada commitado antes desta finalização.** Ver a seção 9 para o que foi commitado e o que ficou fora de propósito.

## 2. Decisões do autor em 2026-11-16 (registro)

| # | Decisão | Onde |
|---|---|---|
| R1 | Reteste de 150 pares (50%), sorteio **estratificado**, `incerto` entra no sorteio, Kappa de 3 classes **e** binário, seed 43 (= 42 + 1, fixada antes de ver rótulos) | `configs/blocagem_pxp.yaml`, spec 001, `tasks-1b` T10c |
| R2 | O reteste foi anotado **39 minutos** depois da primeira passada (erro de calendário meu: gerei a planilha cedo e sem trava; o autor decidiu seguir por prazo). **Desvio do ADR-0005**, declarado | **ADR-0016** (Proposto), `main.tex` §4.1 |
| R3 | `incerto` **não** vira terceira classe do modelo por ora; reavaliar depois de contar os `incerto` da B2 | memória `decisao-incerto-como-classe-adiada` |
| R4 | Adjudicação em arquivo separado, formato A (15 colunas do teste, fonte no prefixo da observação) | `anotacoes_teste_pxp_adjudicacao.csv` |
| R5 | Terceira fonte `autor:` (julgamento do próprio autor, sem consulta); no teste final vira `autor_adjudicacao`; reportar **com e sem** esses pares. Dois pares "Não é possível saber…" voltaram a `incerto` | **ADR-0018 (Aceito)**, protocolo §3.5 emendado |
| R6 | ADR-0005 (cabeçalho) e `main.tex` §4.1 atualizados com os dois desvios | feito |
| R7 | CPT, se vier, será o **ADR-0017** | `pendencias_autor.md` E5 |
| P5 | D1 a D6 da TAIL aprovados; **D1 (tamanho) vale para variantes E notas fiscais**; sem holdout da TAIL (D3); teto de 10 pares por grupo de NF (D4); negativos só com tamanho diferente, razão 1:1 (D5); marca trocada pelo LLM aceita e declarada (D6) | `configs/pares_tail_pxp.yaml` |

## 3. Artefatos e hashes (os que NÃO se regeneram)

| Arquivo (`dados/processados/`) | Conteúdo | SHA-256 (início) |
|---|---|---|
| `anotacoes_teste_pxp.csv` | primeira passada, 300 pares (140 `match`, 141 `nao_match`, 19 `incerto`) | `859fdc8b…` |
| `anotacoes_teste_pxp_adjudicacao.csv` | 19 pares: 2 `match`, 7 `nao_match` (todos `autor:`), 10 `incerto` | `f46b72b9…` |
| `anotacoes_teste_pxp_reteste.csv` | 150 pares reanotados | `a56b5767…` |
| `anotacoes_treino_b2_pxp.csv` | B2, 3.974 pares, **0 anotados** | `82d464c2…` |
| `pares_teste_pxp.csv`, `pares_b2_pxp.csv`, `pool_cego/*`, `anotacoes_amostra_cega.csv` | sorteios e pool (ver doc de 13/11) | |

**Backup local (não definitivo):** `~/Desktop/TCC_backup_2026-11-16/` (13 arquivos, `SHA256SUMS`). Há também cópias intermediárias soltas no Desktop. Esses arquivos têm descrições reais da ALTA.

**Regeneráveis** (rodar `uv run python scripts/03_construcao_dataset.py`, ~50 s): `teste_pxp.parquet` (só com `--teste`), `pares_tail_pxp.parquet`, `treino_pxp.parquet`, `validacao_pxp.parquet`, partição, métricas.

## 4. Comandos do script 03

| Comando | Efeito |
|---|---|
| `uv run python scripts/03_construcao_dataset.py` | 1a, 1b, partição, parte A, **TAIL** (se `dados/brutos/tail` existir), treino. Idempotente, nunca reescreve planilha do autor |
| `… --adjudicacao` | gera a planilha de adjudicação; se existe, só valida |
| `… --teste` | compõe `teste_pxp.parquet` e `resultados/metricas/teste_pxp_resumo.csv` |
| `… --reteste` | gera a planilha do reteste (já gerada) |
| `… --kappa-reteste [--aceitar-intervalo-curto]` | Kappa do reteste; sem o aceite recusa se < 7 dias. O CSV traz `intervalo_minimo_cumprido` |

## 5. Números de referência novos

- **Kappa do reteste (intervalo de 0,65 h, `intervalo_minimo_cumprido=False`):** 3 classes **0,8125**, binário **0,8955** (150 pares; 134 sem `incerto`). Limite superior da consistência, **não** é teste-reteste de 7 dias. Dos 15 `incerto` da primeira passada que voltaram: 7 repetiram, 3 viraram `match`, 5 viraram `nao_match`.
- **Teste final por estrato** (`teste_pxp_resumo.csv`): `[0.00,0.50)` 8 (0 `match`); `[0.50,0.70)` 20 (1); `[0.70,0.90)` 94 (41); `[0.90,1.00]` 97 (88); `digito_divergente` 59 (0); `texto_identico` 12 (12). `prob_inclusao` de 2,3e-05 a 0,040. **O teste é estratificado:** métrica agregada exige ponderar por `1/prob_inclusao` ou relatar por estrato.
- **TAIL:** 23.758 pares (11.719 `tail_variante`, 160 `tail_nf`, 11.879 `tail_negativo`). Das 26.927 variantes únicas, 11.543 do `old_attack` preservam o tamanho (+176 do `attack.csv`). Maior cosseno de título da TAIL com o benchmark: **0,684** (0 exclusões a 0,9). O `octaprice` tem 18.084 URLs em 3 formatos.
- **Benchmark da TAIL (`dados/brutos/tail/pairs_to_label.csv`):** 1.200 pares, 30 positivos. O clone tem duas cópias que **diferem em 4 rótulos** (`dados/` = 30 positivos, `data/` = 28); usei a de `dados/`. **Não verificado** qual a TAIL confirmou.
- Os arquivos de **predições da TAIL** (`pairs_normalized*.csv`, `baseline_predictions.csv`) **não foram copiados** para `dados/brutos/tail/`. O McNemar contra a TAIL (ADR-0013 item 6) os exige.

## 6. O que falta

**Do autor** (detalhes em `pendencias_autor.md`)
- B2 (A5): anotar; revela quantos `incerto` o treino teria e decide o ADR de 3 classes.
- Backup definitivo (B1), autorizações ALTA/Dharma/TAIL (C1 a C3), orientador (C4: levar ADR-0013, ADR-0016, ADR-0018 e a partição).
- GPU/VRAM, `load_in_4bit` × ADR-0003, licença LLaMA, instalar o extra `finetuning` (D1 a D4).
- Revisar o ADR-0015 ("Proposto") e o ADR-0016 ("Proposto"); tabela de abreviações (E7); diário (E3); `main.tex` (resto de E2).
- Reconsiderar nada novo na adjudicação: está fechada.

**Do Claude, em ordem**
1. **Harness de avaliação e baselines** (specs 002 e 004, scripts 04 e 06): **próximo bloco**, começa com um plano completo (`docs/prompt_planejamento_harness.md`). Pode andar sem GPU, exceto o LLaMA zero-shot.
2. Script 05 (spec 003): depende de D1 a D4.
3. Fatia produto × dicionário (RF6, teste de 100 pares, treino): depende de A4 e da D-5.
4. Tabela de Kappa por script 06 para o `main.tex` (o texto tem um marcador `% [VERIFICAR]`).

## 7. Regras de trabalho (valem sempre)

TDD com parada no RED para o autor ver; `make check` verde; **nenhum commit sem o autor pedir** (hoje ele pediu, ver seção 9) e **nunca push** sem pedido explícito (o repositório é **público**); nenhum LLM ou gerador gera ou rotula teste ou validação; só o autor anota; Cross-Encoder é a única arquitetura; nada da TAIL é versionado ou publicado; `codg_item`/`desc_ref`/`match_score` nunca entram em rótulo, treino, validação, blocagem ou planilha; antes de editar protocolo, ADRs ou `main.tex`, pedir aval; plano curto e confirmação antes de cada bloco grande; tudo ou nada nas funções que gravam; nunca sobrescrever planilha do autor; falhar alto.

## 8. Armadilhas

- **`make clean` apaga `dados/processados/*.csv`**, incluindo as planilhas anotadas (não está no documento de 13/11). Não rodar. `git clean` e `git stash -u` têm o mesmo risco.
- **`git add -A` é perigoso:** as quatro planilhas `anotacoes_*.csv` casam com a exceção `!anotacoes*.csv` do `.gitignore`, e `proposta_tcc.docx` está solto na raiz. Adicionar por caminho.
- **O `main()` agora roda a TAIL** quando `dados/brutos/tail` existe (~35 s, ~1 GB). Nos testes, `_registrar_etapas_do_main` aponta `DADOS_BRUTOS_TAIL` para um caminho inexistente; sem isso o teste rodaria a TAIL real.
- **Não gerar planilha de etapa com intervalo mínimo antes da data** (lição do reteste). Uma trava no `--reteste` foi proposta e não implementada.
- **O anotador local** (`ferramentas/anotador_teste.html`) abre pelo Chrome ou Edge. Um salvamento dele com "sobrescrever" desfaz edições feitas por script.
- zsh: `echo ======` falha; macOS: `sed -i ''`. O formatador pode converter escapes `﻿` em caractere invisível nos testes: usar `_BOM = "﻿"`.
- Contar pares únicos, não linhas direcionadas do ranking.

## 9. Commits desta finalização (2026-11-16)

Commitados **localmente**, sem push, na branch `feat/blocagem-produto-x-produto`. Ficaram **fora de propósito:** as quatro planilhas `anotacoes_*.csv` anotadas, o `proposta_tcc.docx` (B4) e tudo em `dados/brutos/tail/` (ignorado pelo git). Conferir com `git log --stat -4` e `git status --short`.

## 10. O que NÃO foi verificado

- Se o repositório remoto é público e se a amostra cega (50 descrições da ALTA) continua em `origin/feat/blocagem-e-fatia-principal` (só o cache local foi visto).
- O texto novo do `main.tex` §4.1 **dentro do PDF** (`pdftotext` ausente; a compilação terminou sem erro).
- Qual cópia do benchmark a TAIL confirmou; a precisão dos positivos da TAIL (marca trocada pelo LLM); quão bem o modelo aprende com 63% de treino vindo de outro domínio.
- O prazo restante das 16 semanas (não está nos documentos lidos).
- `torch`/`peft` em Python 3.14 em execução; GPU e VRAM da Dharma-AI.
- As specs 002 e 004 **não foram lidas nesta sessão**: o plano do harness parte delas.
