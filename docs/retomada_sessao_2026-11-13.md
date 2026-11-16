# Retomada: estado completo do TCC em 2026-11-13

> **SUBSTITUÍDO por `docs/retomada_sessao_2026-11-16.md`** (reteste, adjudicação, teste final e TAIL). Este arquivo fica como referência histórica; os números e os 746 testes abaixo são de 13/11.

> **Escrito para:** o autor e para uma sessão nova do Claude Code que comece do zero, sem nenhum contexto desta conversa.
> **Lista viva de pendências (a que se marca):** `docs/pendencias_autor.md`. A seção 8 daqui é só uma fotografia dela em 2026-11-13.
> **Memória do Claude:** `~/.claude/projects/-Users-pedrohmv-TCC/memory/` (o `MEMORY.md` aponta para este arquivo).

---

## 0. Como usar este documento

**Para o autor.** Leia a seção 8 (o que só você faz) e a seção 9 (o que o Claude faz a seguir). O resto é referência. Se for começar uma sessão nova, cole o prompt da seção 0.1.

### 0.1 Prompt para colar numa sessão nova

```
Retomada do TCC "Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned" (UFPB, autor Pedro). Responda em português.

Antes de qualquer ação, leia, nesta ordem: CLAUDE.md, AGENTS.md, docs/retomada_sessao_2026-11-13.md (este é o resumo completo do estado), docs/pendencias_autor.md, docs/adr/0004, 0010, 0011, 0013, 0014 e 0015, specs/001-construcao-dataset-ground-truth/{requirements,design-1b,design-treino-pxp,tasks-1b}.md, docs/protocolo_anotacao.md e a memória retomada-1-2b-blocagem-produto-x-produto (em ~/.claude/projects/-Users-pedrohmv-TCC/memory/).

Regras de trabalho (valem para tudo): TDD, com testes primeiro e parada no RED para o autor ver; gate `make check` verde; NENHUM commit sem o autor pedir; nenhum LLM ou gerador gera ou rotula teste ou validação; só o autor anota; Cross-Encoder é a única arquitetura; nada da TAIL é versionado ou publicado; não instale o extra `finetuning` sem o autor mandar; antes de editar documentos (protocolo, ADRs, main.tex) peça o aval; proponha um plano curto e confirme antes de cada bloco grande.

Primeira ação: faça o P0 da seção 11 do documento de retomada (git status, make check esperando 746 testes verdes, hashes das planilhas, quantas linhas já foram anotadas nas duas planilhas). Depois me diga o que mudou desde 2026-11-13 e proponha o próximo bloco, escolhendo entre os da seção 9 conforme o que eu já tiver anotado e respondido. Pare nesse checkpoint antes de codar.
```

### 0.2 Prompt de entendimento (somente leitura): para se situar antes de agir

Use este quando quiser apenas **entender o estado, as pendências e os próximos passos**, sem que a sessão altere nada. O da seção 0.1 já parte para a ação; este não.

```
Você está retomando o TCC "Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned" (UFPB, autor Pedro) numa sessão nova, sem contexto prévio. Responda em português. Esta sessão é SOMENTE DE LEITURA E ENTENDIMENTO: não edite nenhum arquivo, não crie arquivos, não rode o pipeline (`scripts/03_construcao_dataset.py`), não instale nada (em especial o extra `finetuning`), não faça commit e não toque nas planilhas de anotação. São permitidos: ler arquivos, `git status`, `git log`, `make check` (só roda testes) e leituras de CSV/parquet para contagens.

Leia, nesta ordem: CLAUDE.md, AGENTS.md, docs/retomada_sessao_2026-11-13.md (o resumo completo do estado), docs/pendencias_autor.md, a memória retomada-1-2b-blocagem-produto-x-produto (em ~/.claude/projects/-Users-pedrohmv-TCC/memory/), docs/adr/0004, 0010, 0011, 0013, 0014 e 0015, e specs/001-construcao-dataset-ground-truth/{requirements,design-1b,design-treino-pxp,tasks-1b}.md. Consulte docs/protocolo_anotacao.md e as specs 002, 003 e 004 só se precisar.

Depois verifique o estado real contra o documento: `git status --short` (o documento diz ~30 caminhos, nada commitado), `make check` (diz 746 testes verdes), o SHA-256 de dados/processados/anotacoes_teste_pxp.csv e de dados/processados/anotacoes_treino_b2_pxp.csv (a seção 5 traz os valores de antes de qualquer anotação) e quantas linhas já estão anotadas em cada planilha (coluna `rotulo` não vazia, separador `;`). Aponte qualquer divergência entre o documento e a realidade, sem corrigi-la.

Entregue, nesta ordem e sem repetir o documento inteiro:
1. O estado em até 10 linhas: o que está pronto, o que está em rascunho e o que ainda é esqueleto.
2. As pendências do AUTOR, separadas por o que elas bloqueiam: (a) o calendário (anotação do teste, reteste de 7 dias); (b) o treino real do modelo (GPU, VRAM, `load_in_4bit`, licença, instalação do extra); (c) a publicação (repositório público, autorizações do ALTA, da Dharma-AI e da TAIL, backup); (d) documentos que esperam o aval dele (ADR-0015, tabela de abreviações, `main.tex`, diário). Para cada grupo, diga o que é mais urgente e por quê.
3. Os próximos passos do CLAUDE, em ordem, marcando para cada um se depende das anotações do autor, se depende de outra pendência dele, ou se pode começar já. Inclua, para o P5 (pares da TAIL), as decisões de desenho que precisam ser fechadas com o autor antes de codar.
4. Os riscos e o que NÃO foi verificado (seção 13 do documento), e as armadilhas que mais podem causar dano (seção 10), em especial o risco de publicar dado da ALTA ou da TAIL num repositório público.
5. No máximo 3 perguntas ao autor, só as que mudam o que você faria a seguir.

Regras que valem para qualquer sessão futura e que você deve respeitar nas recomendações: TDD com parada no RED para o autor ver; nenhum commit sem o autor pedir; nenhum LLM ou gerador gera ou rotula teste ou validação; só o autor anota; Cross-Encoder é a única arquitetura; nada da TAIL é versionado ou publicado; antes de editar documentos (protocolo, ADRs, main.tex) pedir o aval; propor um plano curto e confirmar antes de cada bloco grande. Não invente: cite o arquivo e a seção de onde veio cada afirmação e diga "não sei" quando o documento não responder.

Termine com uma única pergunta: "Por qual bloco você quer começar?", listando os 2 ou 3 que fariam mais sentido agora e por quê.
```

**Versão curta**, se o contexto estiver apertado:

```
Leia CLAUDE.md, docs/retomada_sessao_2026-11-13.md e docs/pendencias_autor.md (nessa ordem), sem editar nem rodar nada além de leituras, `git status` e `make check`. Em português, me diga em no máximo 25 linhas: (1) o estado do projeto, (2) o que SÓ EU posso fazer e o que cada coisa bloqueia, (3) o que você pode fazer sem mim, em ordem, (4) o que diverge entre o documento e o estado real do repositório. Termine perguntando por qual bloco começar.
```

---

## 1. O projeto em poucas linhas

- **TCC:** *Entity Matching em Produtos de Supermercado com Small Language Models Fine-Tuned*. Curso de Ciência de Dados para Negócios, UFPB. Orientador: Prof. Hilton Martins de Brito Ramalho. Execução individual, 16 semanas, dedicação parcial. Vinculado ao projeto CNPq/ALTA (monitoramento de preços em PB/CE/PI) e à infraestrutura da Dharma-AI.
- **Problema:** decidir se duas descrições de produto (ruído de PDV) são o mesmo SKU.
  - **Fatia principal (ADR-0014): produto × produto**, entre lojas, regra de SKU (marca, variante e tamanho decidem).
  - **Fatia secundária: produto × dicionário canônico** (~1.593 entradas, categoria e variante decidem; tamanho e marca não).
- **Método:** fine-tuning de um SLM (LLaMA 3.2 3B, ADR-0002) como **Cross-Encoder** (ADR-0001), com **LoRA bf16 sem quantização** (ADR-0003), **um adaptador por tipo de par** (ADR-0013). Plano de contingência de GPU no ADR-0009.
- **Fonte da verdade:** a proposta v3 (objetivos, metodologia, cronograma), os ADRs (decisões) e as specs (implementação). O ADR-0014 inverte a prioridade das fatias em relação à proposta v3; o `main.tex` ainda não foi atualizado (tarefa 5.3).

### 1.1 Restrições inegociáveis (resumo; a lista completa está no `CLAUDE.md`)

1. LaTeX é a única saída de texto do TCC (nunca `.docx` para o texto final).
2. Cross-Encoder é a única arquitetura (Bi-Encoder e híbrido são trabalho futuro).
3. **Nenhum gerador ou LLM** (Dataset Generator, `attack_augmentation` da TAIL, LLM-as-judge, predições de LLM) **gera ou rotula teste ou validação** (ADR-0004, emendado pelo 0013). Só o autor anota.
4. Duas regras de match, uma por tipo de par; dois adaptadores LoRA.
5. Nada da TAIL é versionado, redistribuído ou publicado sem autorização escrita (uso local autorizado verbalmente pelo dono do projeto; ver seção 4).
6. `codg_item`, `desc_ref` e `match_score` (matching pré-existente do ALTA) **nunca** entram em rótulo, treino, validação, blocagem, seleção de pares ou planilha (ADR-0010/0011); há `assert` no script.
7. Nenhuma entrada em `referencias.bib` sem verificação em fonte primária.
8. Seeds fixas e YAML versionado em toda etapa estocástica (seed 42 em tudo).
9. Partição por componente **antes** de qualquer geração ou aumentação.
10. Blocagem é TF-IDF/BM25 clássico, não arquitetura aprendida.

---

## 2. Regras de trabalho acordadas com o autor

- **TDD em três camadas** (`AGENTS.md` §3): unitário puro; transformação em memória com fixtures; integração leve em `tmp_path`. **Paro no RED** para o autor ver os testes falhando e só implemento depois do "pode seguir". (Exceção: o autor autorizou ir do RED ao GREEN direto em integrações específicas no P1.)
- **Gate:** `make check` (ruff + mypy + pytest). Estado atual: **746 testes verdes**.
- **Nenhum commit sem o autor pedir.** Nada desta sessão está commitado.
- **Antes de editar documentos** (protocolo, ADRs, `main.tex`), pedir o aval. Mudança de decisão registrada em ADR exige ADR novo.
- **Proponha um plano curto e confirme antes de cada bloco grande.**
- **Não instalar o extra `finetuning`** (`torch`, `transformers`, `peft`, `accelerate`) enquanto o autor não mandar.
- **Tudo ou nada** nas funções que gravam artefatos; **nunca sobrescrever** o que o autor anota; **falhar alto** em vez de reduzir ou corrigir em silêncio.
- **Relatar fielmente:** erros próprios, números corrigidos e o que não foi verificado vão para o autor sem rodeio (ver seção 12).
- **Idioma:** português em tudo, inclusive código, mensagens de erro e commits.

---

## 3. O que foi feito, em ordem

### 3.1 Antes desta sessão (estado de partida, informado pelo autor em 2026-11-13)

- Scripts 01 (coleta e limpeza) e 02 (EDA) prontos. 1a (produto × dicionário) congelada em TF-IDF k=20. 1b (produto × produto), tarefas T0 a T10, prontas: blocagem congelada em **TF-IDF, k=20** (recall por par 93,8%, IC95% por bootstrap 88,9–98,6%; 81 positivos; 33 de 75 âncoras com positivo), alocação do teste decidida e **300 pares do teste sorteados** em `dados/processados/pares_teste_pxp.csv` (sem rótulo).
- O autor anotou o **pool**: 3 lotes de 25 âncoras, 11.008 pares (81 `match`, 37 `incerto`, o resto não-match implícito), 8.598 produtos distintos.
- Esqueletos (`NotImplementedError`): scripts 04, 05 e 06; `modelos/` vazio.
- Havia 26 testes em RED (`test_transformacao_planilha_teste_pxp.py`) deixados de propósito.

### 3.2 Nesta sessão (2026-11-13), por bloco

| Bloco | O que entrou | Estado |
|---|---|---|
| **P0** | Verificação do estado: `make check` com 26 falhas esperadas e 361 passando. | feito |
| **P1 / T10b** | Planilha do teste p×p: `montar/validar/gravar/gerar_planilha_teste_pxp`; `ferramentas/anotador_teste.html` (um par por tela, teclas M/N/I/X/O); teste de contrato HTML × script. Planilha real gerada. | GREEN |
| **P2 / T11** | Partição por componente conexo: `componentes_conexos`, `particionar_componentes`, `verificar_particao_por_componente`, `vazamento_residual`, `resumir_particao`, `gerar_particao_pxp`. `proporcao_treino` removida (chave obsoleta, rejeitada). | GREEN |
| **P3 / T12** | `montar_validacao_pxp`, `montar_produtos_treino_pxp`, `gerar_conjuntos_pxp`; fiação das etapas 3 a 5 em `executar_blocagem_pxp` (`_etapas_pos_pool`); `main()` roda 1a e 1b; CA-1b-01 a 07 marcados na spec. | GREEN |
| **Documentos** | `design-1b.md`, `tasks-1b.md`, `requirements.md` (RF2 reescrita, regra das partições), READMEs, `pendencias_autor.md`. | feito |
| **P4 / B2** | Investigação de viabilidade da supervisão distante (inviável); opção B2 escolhida; `selecionar_pares_b2`, `montar/validar/gravar_planilha_b2`, `gerar_planilha_b2_pxp`; `b2_cosseno_minimo` na config. Planilha da B2 gerada. | GREEN |
| **ADR-0015** | Rascunho (status "Proposto"); emenda no cabeçalho do ADR-0004; RF2 reescrita. | aguardando revisão do autor |
| **Parte A do treino** | Perturbações (`perturbar_unidade/ordem/abreviacao/ruido_tipografico`), `ranquear_vizinhos`, `selecionar_negativos_tamanho`, `gerar_negativos_tamanho`, `gerar_positivos_perturbados`, `montar_pares_treino_auto`, `verificar_pares_treino_auto`, `gerar_pares_treino_auto_pxp`, `carregar_config_treino_pxp`, `configs/pares_treino_pxp.yaml`. | GREEN |
| **TAIL (medição)** | Inventário e medição do clone `invoice-data-normalizer/` (seção 7.6). Só leitura. | feito |
| **Montagem do treino** | `ingerir_anotacao_b2`, `montar_treino_pxp`, `verificar_treino_pxp`, `gerar_treino_pxp`; `treino_pxp.parquet` gerado só com a parte A. | GREEN |

---

## 4. Decisões do autor (registro com datas)

Todas de **2026-11-13**, salvo indicação.

| # | Decisão | Onde está registrada |
|---|---|---|
| D1 | **Partição:** τ = 0,7 mantido; teste = componentes que tocam os 300 pares; validação = componentes tocados pelo pool (fora do teste); treino = o restante. **Sem proporção 80/20** (`proporcao_treino` virou chave obsoleta). Alternativas medidas e descartadas: τ = 0,8 e ampliar o pool. | `requirements.md` RF1 "1b"; `design-1b.md` C9; `blocagem_pxp.yaml` |
| D2 | **Q1:** o pool anotado vai para a **validação** (não para teste nem treino). | `requirements.md` (tabela de perguntas) |
| D3 | **Rótulo da validação = anotação do autor (pool)**, nunca a heurística. Não escolher limiar por F1 bruto na validação: usar PR-AUC e reponderar ou subamostrar negativos para a prevalência-alvo. | memória; `requirements.md` |
| D4 | **TAIL:** sem autorização escrita; o dono do projeto autorizou por áudios e WhatsApp; o autor decidiu prosseguir como se autorizada, **só uso local** (treino e avaliação). `main.tex` mantém `[a confirmar]`. | `pendencias_autor.md` C3; ADR-0013 |
| D5 | **Opção B2** para os pares de treino: o autor anota os pares do treino com mesmo tamanho e cosseno TF-IDF ≥ 0,5 (3.974 pares), em cartão por par, com rótulo explícito, na mesma ferramenta do teste. | `design-treino-pxp.md` §8; ADR-0015 |
| D6 | **Reescrever a RF2 por ADR novo** (ADR-0015, supervisão distante por marca + tamanho abandonada). | ADR-0015; `requirements.md` RF2 |
| D7 | **Receita de perturbação aprovada** (unidade, ordem, abreviação, ruído). | `design-treino-pxp.md` §5 |
| D8 | **Incluir negativos da mesma loja** (`incluir_mesma_loja: true`). | `pares_treino_pxp.yaml`; ADR-0015 |
| D9 | **Tabela fechada de abreviações** no YAML, revisável pelo autor (a mineração automática foi descartada). | `pares_treino_pxp.yaml`; pendência E7 |
| D10 | **Nomes dos arquivos:** `treino_pxp.parquet`, `validacao_pxp.parquet`, `teste_pxp.parquet` (o p×d terá os seus). | memória; README dos dados |
| D11 | **Não instalar o extra `finetuning` ainda.** | este documento |
| D12 | Ritmo: RED, parada, aval, GREEN. | seção 2 |

---

## 5. Linhagem dos dados e do pipeline

```
dados/brutos/ (imutáveis, ALTA)                       [script 01]
   └─► produtos_limpos.parquet (29.130 registros) + dicionario_limpo.parquet (1.593) + relatorio_limpeza.json
          │                                           [script 03, 1a: produto × dicionário]
          ├─► anotacoes_amostra_cega.csv (50 produtos) → recall_blocagem.csv → candidatos_blocagem.parquet
          │                                           [script 03, 1b: produto × produto]
          └─► universo (texto normalizado, loja) = 28.921 produtos em 8 lojas
                 ├─► pool_cego/lote_01..03.csv (+ ancoras_lote_NN.csv)  ← anotado pelo autor
                 │      └─► recall_blocagem_pxp.csv, tab_recall_blocagem_pxp.tex, taxas_positivos_por_faixa_pxp.csv
                 ├─► pares_teste_pxp.csv (300 pares, sem rótulo) ─► anotacoes_teste_pxp.csv (autor anota)
                 ├─► componentes_pxp.parquet (componente + partição de cada produto)
                 │      ├─► validacao_pxp.parquet (pares do pool na validação, rótulo do autor)
                 │      └─► produtos_treino_pxp.parquet (só produtos de treino)
                 │             ├─► pares_treino_auto_pxp.parquet (parte A)
                 │             ├─► pares_b2_pxp.csv ─► anotacoes_treino_b2_pxp.csv (autor anota)
                 │             └─► (futuro) pares_tail_pxp.parquet (P5)
                 │                    └─► treino_pxp.parquet = A + B2 anotado + TAIL
                 └─► (futuro) teste_pxp.parquet = ingestão da anotação do teste
```

**Tabela de artefatos** (todos em `dados/processados/`, exceto indicação; **fora do git** por `dados/processados/*`, salvo `anotacoes*.csv` e o README):

| Arquivo | Conteúdo | Tamanho / hash |
|---|---|---|
| `produtos_limpos.parquet` | base limpa, sem colunas da ALTA | 29.130 registros |
| `anotacoes_amostra_cega.csv` | amostra cega p×d (50 produtos) | sha `38846661…`; **versionável e já está no remoto público** |
| `pool_cego/lote_01..03.csv` | pool anotado | 3.825 + 3.464 + 3.719 linhas; sha `3f964963…`, `bc6beb06…`, `98382136…` |
| `pares_teste_pxp.csv` | 300 pares sorteados, com `estrato` e `prob_inclusao`, sem rótulo | sha `00e77881…` |
| `anotacoes_teste_pxp.csv` | **planilha do teste, 300 linhas, 0 anotadas** | sha `67a6583c0dc123775112bb304e134772854caa0982d20a23da0c21b843d53044` (enquanto não houver anotação) |
| `componentes_pxp.parquet` | 28.921 produtos × (componente, partição) | |
| `validacao_pxp.parquet` | 5.906 pares únicos (25 `match`, 5.881 `nao_match`) | |
| `produtos_treino_pxp.parquet` | 12.656 produtos | |
| `pares_treino_auto_pxp.parquet` | 14.200 pares (parte A) | |
| `pares_b2_pxp.csv` | 3.974 pares congelados (`id_a`, `id_b`, `score`) | sha `a471b855…` |
| `anotacoes_treino_b2_pxp.csv` | **planilha da B2, 3.974 linhas, 0 anotadas** | sha `82d464c2279de4beed8fab2e43dff4eacc7033cda171def026fb55b0b38e0876` (enquanto não houver anotação) |
| `treino_pxp.parquet` | 14.200 pares hoje (só parte A) | |
| `resultados/metricas/*.csv` | métricas e resumos (também ignorados pelo git) | |

> Os hashes das planilhas só valem **antes** de o autor anotar: depois de anotar, o hash muda de propósito. O que nunca pode mudar sozinho é o conteúdo das colunas de texto e dos ids.

---

## 6. Mapa do código

### 6.1 `scripts/03_construcao_dataset.py` (3.142 linhas)

Seções, na ordem do arquivo, com as funções públicas:

| Seção | Funções e constantes principais |
|---|---|
| 1a (produto × dicionário) | `carregar_config`, `deduplicar_por_texto_normalizado`, `ranquear_tfidf/bm25`, `sortear_amostra_cega`, `montar_planilha_amostra_cega`, `validar_anotacao_amostra_cega`, `calcular_recall_por_k`, `montar_tabela_recall_tex`, `executar_blocagem` |
| 1b: universo e ranking | `carregar_config_pxp`, `deduplicar_por_texto_e_loja`, `tokens_numericos`, `divergencia_numerica`, `ranquear_entre_lojas`, **`ranquear_vizinhos`** (inclui a mesma loja), `ranquear_ngramas` |
| 1b: pool | `sortear_ancoras`, `decidir_proximo_lote`, `montar_pool`, `montar_planilha_pool`, `gravar_planilha_pool`, `validar_anotacao_pool`, `resumir_ancoras_pool`, `calcular_recall_pxp`, `montar_tabela_recall_pxp_tex`, `executar_blocagem_pxp`, `_etapas_pos_pool` |
| 1b: teste | `taxas_positivos_por_faixa`, `sortear_pares_teste`, `gerar_pares_teste_pxp` |
| Planilha do teste | `montar/validar/gravar/gerar_planilha_teste_pxp` (parametrizadas por `origem`, `nome` e `nome_arquivo` para a B2 reaproveitar) |
| B2 | `selecionar_pares_b2`, `montar_planilha_b2`, `validar_anotacao_b2`, `gravar_planilha_b2`, `gerar_planilha_b2_pxp` |
| Partição | `componentes_conexos`, `verificar_particao_por_componente`, `particionar_componentes`, `vazamento_residual`, `resumir_particao`, `gerar_particao_pxp` (cálculo em `_calcular_particao_pxp`, gravação em `_gravar_particao_pxp`) |
| Conjuntos da partição | `montar_validacao_pxp`, `montar_produtos_treino_pxp`, `gerar_conjuntos_pxp` |
| Parte A | `carregar_config_treino_pxp`, `perturbar_*`, `_blocos`, `_preserva_tamanhos`, `selecionar_negativos_tamanho`, `gerar_negativos_tamanho`, `gerar_positivos_perturbados`, `montar_pares_treino_auto`, `verificar_pares_treino_auto`, `gerar_pares_treino_auto_pxp` |
| Montagem do treino | `ingerir_anotacao_b2`, `montar_treino_pxp`, `verificar_treino_pxp`, `gerar_treino_pxp` |
| Pendente | `particionar_por_produto_canonico` (só a fatia p×d, RF6, `NotImplementedError`); `main()` |

**Fluxo do `main()`** (`uv run python scripts/03_construcao_dataset.py`, ~12 s, idempotente): `executar_blocagem` (1a) → `executar_blocagem_pxp` (1b; depois da parada do pool, se método/k estão congelados e `n_por_estrato` existe: sorteia o teste uma vez, valida a planilha do teste, partição e conjuntos, e a planilha da B2 se `b2_cosseno_minimo` existe) → `gerar_pares_treino_auto_pxp` (se há `produtos_treino_pxp.parquet`) → `gerar_treino_pxp` (se há `pares_treino_auto_pxp.parquet`).

**Padrões que se repetem (respeitar nas próximas funções):** compute-then-write (tudo ou nada); `AssertionError` explícito (e não `assert`) nas barreiras críticas, para valer com `python -O`; `ValueError` nomeando a faixa, o id ou a chave que falhou; planilha do autor só é lida, nunca reescrita; ids de pares são `_hash_curto("a|b")` com `a < b`; texto e unidade vêm sempre do universo, nunca da planilha.

### 6.2 Outros arquivos

- **Configs:** `configs/blocagem.yaml` (1a), `configs/blocagem_pxp.yaml` (1b, inclui `b2_cosseno_minimo: 0.5`, `tau_particao: 0.7`, alocação do teste), `configs/pares_treino_pxp.yaml` (parte A), `configs/eda.yaml`.
- **Ferramentas:** `ferramentas/anotador_pool.html` (anotador do pool, âncora + lista) e `ferramentas/anotador_teste.html` (cartão por par; **abre os dois arquivos**, `anotacoes_teste_pxp.csv` e `anotacoes_treino_b2_pxp.csv`). Abrir no Chrome ou Edge (salvamento automático no arquivo).
- **ADRs:** `docs/adr/0001` a `0015` (0015 é rascunho).
- **Specs:** `specs/001` (dataset; `design-1b.md`, `tasks-1b.md`, `design-treino-pxp.md`), `002` (baselines), `003` (fine-tuning), `004` (avaliação), `005` (escrita LaTeX).
- **Docs:** `protocolo_anotacao.md` (regras de match por tipo de par), `pendencias_autor.md`, `plano_desenvolvimento.md`, `diario_pesquisa.md` (sem entrada depois de 2026-10-31), `limpeza_dados.md`, `resultado_blocagem_amostra_cega.md`, `relatorio_impacto_tail.md`.
- **Skills do projeto** (`.claude/skills/`): `abnt-latex`, `avaliacao-baselines`, `dominio-entity-matching`, `protocolo-anotacao-em`, `reprodutibilidade-ml`, `verificacao-citacoes`.

### 6.3 Testes (746 verdes)

| Arquivo | Camada | Cobre |
|---|---|---|
| `test_unitario_perturbacoes_pxp.py` (161) | 1 | as quatro perturbações, bug do tamanho com espaço, `carregar_config_treino_pxp` |
| `test_unitario_blocagem_pxp.py` (119) | 1 | config 1b, tokens numéricos, pool, recall, `b2_cosseno_minimo` |
| `test_transformacao_blocagem_pxp.py` (94) | 2 | ranking entre lojas, pool, sorteio do teste |
| `test_integracao_pipeline.py` (91) | 3 | 1a, 1b, partição, conjuntos, B2, parte A, treino, `main()` |
| `test_transformacao_b2_pxp.py` (33) | 2 | seleção e planilha da B2 |
| `test_transformacao_pares_treino_pxp.py` (27) | 2 | negativos, positivos, barreira da parte A |
| `test_transformacao_planilha_teste_pxp.py` (26) | 2 | planilha do teste |
| `test_unitario_particao_pxp.py` (22), `test_transformacao_particao_pxp.py` (20) | 1 e 2 | partição e componentes |
| `test_transformacao_treino_pxp.py` (21) | 2 | ingestão B2, montagem, barreira do treino |
| `test_transformacao_conjuntos_pxp.py` (17) | 2 | validação e produtos de treino |
| `test_unitario_anotador_teste.py` (3) | 1 | contrato colunas/rótulos do HTML |
| demais | | `test_unitario_blocagem.py`, EDA, limpeza, coleta, heterogeneidade, fixtures de domínio |

---

## 7. Números de referência

### 7.1 Base
- 29.130 registros após limpar duplicatas exatas; 28.240 textos normalizados distintos (1a); **28.921 produtos (texto normalizado × loja) em 8 lojas** (1b).
- Lojas no treino: `extra_api` 4.541, `guedes_api` 3.675, `pinheiro_api` 2.076, `chegou_a_feira_api` 834, `ajuba_api` 545, `diniz_api` 523, `atacadao_api` 330, `mateus_api` 132.
- 1a (p×d): TF-IDF k=20 congelado; 1.959 de 28.240 produtos (6,9%) ficam sem candidato (ADR-0014); amostra cega: 4 de 42 sem a entrada correta no top-100.

### 7.2 Blocagem p×p e pool
- Congelada em **TF-IDF, k=20**. Recall por par **93,8%** (IC95% por âncora 88,9–98,6%); BM25 em k=20: 95,1%, sem diferença estatística. 75 âncoras sorteadas, 33 com positivo, 81 positivos, 37 `incerto`.
- Composição do pool: 53,6% dos candidatos têm tamanho diferente, 33,0% mesmo tamanho, 13,4% sem tamanho num lado; os 81 `match` estão todos entre os de mesmo tamanho (1,08 por âncora).
- Ritmo do autor no pool (timestamps): 3/11, lote 2 gerado 16:47 e concluído 17:10–17:58, lote 3 gerado 17:59 e concluído 18:05–18:21 (≤ 22 min para 25 âncoras e 3.719 candidatos); mediana de 0,7 min por âncora.

### 7.3 Teste
- 300 pares: `texto_identico` 12, `digito_divergente` 60, `[0.90, 1.00]` 100, `[0.70, 0.90)` 100, `[0.50, 0.70)` 20, `[0.00, 0.50)` 8. ~45% de positivos esperados (faixa plausível 33–53%); 600 produtos distintos. O teste é estratificado: métricas agregadas pedem ponderação por `1/prob_inclusao` ou relato por estrato (spec 004).

### 7.4 Partição (τ = 0,7)

| Partição | Componentes | Produtos | % da base | Maior componente |
|---|---|---|---|---|
| treino | 8.682 | 12.656 | 43,8% | 50 |
| validação | 3.650 | 9.953 | 34,4% | 132 |
| teste | 175 | 6.312 | 21,8% | 452 |

- Validação: 5.929 linhas do pool, **5.906 pares únicos** (23 vistos dos dois lados, sem conflito): **25 `match`**, 5.881 `nao_match`; 21 `incerto` fora. 56 dos 81 `match` do pool caíram em componentes do teste.
- **Vazamento residual: 23 de 81 positivos (28,4%)** com lados em componentes diferentes. Sensibilidade (só informativa): τ = 0,8 deixaria 52 `match` e 57,9% de treino, com vazamento residual 56,8%.

### 7.5 Pares de treino produto × produto
- **Medições de viabilidade (validação do autor, só para medir):** tamanho do texto concorda com a coluna da loja em 99,99% (11.279 de 11.280); **tamanho diferente ⇒ não-match: 3.283 de 3.283**; marca (léxico automático) + tamanho: precisão **3,1%** (350 disparos, 11 `match`); cosseno ≥ 0,7 + tamanho: 15,7%; só mesmo tamanho: 1,6%.
- **Contagens em pares únicos** (as primeiras versões estavam infladas, ver seção 12), top-20 TF-IDF no treino: 180.037 pares entre lojas, 91.916 de tamanho diferente, 56.731 de mesmo tamanho, 31.390 com algum lado sem tamanho. Negativos por tamanho por faixa de cosseno: [0, 0,2) 37.584; [0,2, 0,3) 37.863; [0,3, 0,5) 14.801; [0,5, 0,7) 1.500; [0,7, 1] 168. Com a mesma loja incluída (top-20 em todas as lojas): [0, 0,3) 47.322; [0,3, 0,5) 31.973; [0,5, 0,7) 4.657 (3.099 com o teto de 3 por produto); [0,7, 1] 898.
- **Parte A gerada:** 14.200 pares = 8.200 negativos (1.500 / 3.000 / 3.000 / 700 por faixa; **5.107 da mesma loja, 62%**) + 6.000 positivos (ordem 2.116, ruído 1.978, unidade 1.333, abreviação 573). Teto de 3 pares por produto.
- **B2:** 3.974 pares entre 3.072 produtos, por faixa de cosseno: [0,5, 0,6) 1.648; [0,6, 0,7) 930; [0,7, 0,9) 1.013; [0,9, 1] 383. Na validação, mesmo tamanho e cosseno ≥ 0,5 contém 92% dos `match` (23 de 25) em 14% dos pares de mesmo tamanho. Estimativa de esforço do autor: 1,5 a 5,5 h; ~430 positivos esperados (extrapolado de 25, ordem de grandeza).
- **Treino hoje:** `treino_pxp.parquet` = 14.200 pares (8.200 `nao_match`, 6.000 `match`); a B2 entra com o que for anotado.

### 7.6 TAIL (clone local `invoice-data-normalizer/`, commit `9d010ec`)

| Arquivo | Conteúdo | Volume |
|---|---|---|
| `poc_diplodocus/data/input/old_attack_dataset.csv` | (original, variante gerada por LLM), sem tipo | 43.047 linhas, 9.610 originais; 16.120 variantes iguais ao original (descartadas) → **26.927 pares únicos** |
| mesmo arquivo, filtro de tamanho | 51,4% dos originais têm tamanho reconhecível; dos que têm, **83,4% das variantes o preservam** (11.543 pares verificados) e 16,6% o corrompem (unidade trocada por letra errada ou tamanho cortado); 13.085 sem tamanho, não verificáveis | |
| `poc_diplodocus/data/input/attack.csv` | variantes tipadas | 601 linhas, 100 originais: erro de digitação 171, abreviação 170, notação de unidade 170, `Fallback_Erro_LLM` 90 (descartar) |
| `itens_nf_normalizados.csv` (= `train_supervised` 152 + `test_supervised` 38) | itens de nota fiscal de supermercado agrupados pelo mesmo nome normalizado | 190 títulos, **19 grupos**, 855 pares positivos (só 19 produtos) |
| `octaprice_mercadolivre_1/2.json` | avaliações com a URL do anúncio | 18.084 URLs → 17.415 títulos distintos (slug); só reserva de negativos |
| `AmostraDescMerc.csv` | descrições de NF-e com categoria | 15.000 linhas, sem pares |
| `main_supersaurus/dados/pairs_to_label.csv` | **benchmark** | 1.200 pares, **2.267 títulos distintos: proibidos no treino e na validação**; só teste externo exploratório; nenhum aparece nos arquivos acima por correspondência exata |

Ressalvas: variantes geradas por LLM podem alterar a marca (não verificável); domínio Mercado Livre (cosméticos e capilares nos exemplos), não supermercado; os 19 grupos de NF são pouquíssimo diversos. Os `normalized` da TAIL são dados de referência dela, não predições dos modelos avaliados por ela (ADR-0013, item 7). O que o clone **não** tem: `dados/brutos/tail/` (não existe), SHA-256 registrado dos artefatos curados.

---

## 8. Pendências do autor (fotografia em 2026-11-13)

> A lista viva, para marcar, é `docs/pendencias_autor.md`. Em caso de divergência, vale aquela.

### A. Caminho crítico (calendário)
- [ ] **A1. Anotar os 300 pares do teste p×p** em `dados/processados/anotacoes_teste_pxp.csv`, com `ferramentas/anotador_teste.html` (Chrome ou Edge). Regra: `protocolo_anotacao.md` §3, produto × produto (mesma marca, variante e tamanho). Rótulos `match`, `nao_match`, `incerto`; vazio = não anotado. Destrava: reteste, Kappa, `teste_pxp.parquet`, qualquer número no teste. **Comece por aqui.**
- [ ] **A2. Resolver os `incerto` do teste** (protocolo §3.5): adjudicar pelo dicionário ou pelos pesquisadores do ALTA; os não resolvidos ficam fora do teste final.
- [ ] **A3. Reteste (ADR-0005):** reanotar às cegas, **≥ 7 dias** depois da primeira passada, ao menos 150 dos 300 pares. Quando a primeira passada acabar, peça ao Claude a planilha de reteste (sorteio com seed, sem os rótulos originais, em nova ordem). Kappa por tipo de par, reportado mesmo abaixo de 0,75.
- [ ] **A4. Teste produto × dicionário:** decidir a amostragem (`[DECISÃO PENDENTE]` da spec 001, Q3) e anotar os 100 pares. Fecha o CA-1b-05.
- [ ] **A5. Anotar a B2** (3.974 pares) em `anotacoes_treino_b2_pxp.csv`, mesma ferramenta e regra. Estimativa 1,5 a 5,5 h. **O treino já lê o que for anotado, em qualquer quantidade**: rodar `uv run python scripts/03_construcao_dataset.py` e o `treino_pxp.parquet` passa a incluí-lo. `incerto` e pendentes ficam de fora.

### B. Dados e publicação (o repositório é **público**: `pedrohmvv/tcc`)
- [ ] **B1. Backup** do que não está no git: 3 lotes do pool, `pares_teste_pxp.csv`, e as duas planilhas conforme forem anotadas. Decidir: remoto privado, ou commit depois da autorização do ALTA (C2).
- [ ] **B2. Dado da ALTA já público:** `anotacoes_amostra_cega.csv` (50 descrições) está no remoto, branch `origin/feat/blocagem-e-fatia-principal`. Decidir: aceitar, pedir autorização ou remover (reescrever histórico só com cuidado; peça antes).
- [ ] **B3. Não commitar as planilhas anotadas** sem decidir B1 e C2: `anotacoes_teste_pxp.csv` e `anotacoes_treino_b2_pxp.csv` aparecem como novos para o git e entrariam num `git add -A` (o nome casa com a exceção `anotacoes*.csv` do `.gitignore`).
- [ ] **B4. `proposta_tcc.docx` solto na raiz** destoa de "LaTeX é a única saída": mover para fora, ignorar ou remover.
- [ ] **B5. Commitar a 1.2b.** Nada da branch `feat/blocagem-produto-x-produto` está commitado (30 caminhos alterados ou novos). Peça o commit; por padrão o Claude deixa de fora as duas planilhas anotadas e o `proposta_tcc.docx`.

### C. Autorizações e avais externos
- [ ] **C1. Dharma-AI:** autorização formal escrita (infra e ferramenta de geração, abertura futura do repositório ou do teste anotado, patente/registro). Não solicitada.
- [ ] **C2. ALTA/CNPq:** autorização para abrir o repositório e o teste anotado. Não confirmada. Bloqueio real de publicação.
- [ ] **C3. TAIL (uso só local):** guardar os áudios e mensagens de WhatsApp **fora do git**; pedir confirmação de texto de uma linha; registrar no diário. `main.tex` mantém `[a confirmar]`.
- [ ] **C4. Orientador:** confirmar formalmente o aval ao ADR-0013 (ata ou e-mail) e validar o protocolo de anotação (ainda não validado com ele). Pauta sugerida: ADR-0014, partição por componente (τ = 0,7), validação com 25 `match`, vazamento residual 28,4%, ADR-0015.

### D. Infraestrutura (bloqueia o treino real, script 05)
- [ ] **D1. Acesso à GPU da Dharma-AI** e VRAM real (gatilho do ADR-0009).
- [ ] **D2. D9:** o ambiente de teste usa `load_in_4bit: True`, contra o ADR-0003 (bf16 sem quantização).
- [ ] **D3. Aceitar a licença do LLaMA 3.2 3B** no Hugging Face.
- [ ] **D4. `torch`/`peft` no Python ≥ 3.14:** verificado que **não estão instalados** (extra `finetuning`), mas o `uv.lock` já resolve `torch 2.14.0` com wheels cp314 (macOS arm64, Linux, Windows), `peft`, `transformers`, `accelerate`. Falta `uv sync --extra finetuning` (alguns GB) e um smoke test. **O autor mandou não instalar ainda.**
- [ ] **D5. Dataset Generator (D-5, suspenso):** decidir, antes da tarefa 1.7, a fonte dos pares produto × dicionário do adaptador secundário. Só bloqueia esse adaptador.

### E. Documentos que dependem do aval do autor
- [ ] **E1. T13 do `tasks-1b.md`:** protocolo §2.2 (como anotar o pool), plano 1.4.3, ADRs e `main.tex` que ainda dizem "a definir" para D-13 e partição, `docs/resultado_blocagem_pxp.md`.
- [ ] **E2. `main.tex` (tarefa 5.3):** atualizar para o ADR-0014; declarar a limitação da validação (25 `match`, rótulo só do autor), o vazamento residual (28,4%) e o fim da supervisão distante por marca.
- [ ] **E3. Diário** (`docs/diario_pesquisa.md`, sem entrada depois de 2026-10-31): registrar partição, limitação da validação, status da TAIL, ADR-0015. O Claude pode redigir uma proposta.
- [ ] **E4. Decidir se a partição merece ADR novo** (hoje está na spec 001 e no `design-1b.md`).
- [ ] **E5. CPT (opcional, "se der tempo"):** exige ADR novo (**0017**: o 0015 é o dos rótulos de treino e o 0016, rascunho de 2026-11-16, é o do reteste com intervalo curto) e emenda da spec 003.
- [ ] **E6. Revisar o texto do ADR-0015** ("Proposto") e, se concordar, mudar para "Aceito". Ao aceitar, sincronizar com o aval do autor: `main.tex` §4 ("supervisão distante"), ADR-0011 (linha de metadado de unidade cita a RF2), `plano_desenvolvimento.md`.
- [ ] **E7. Revisar a tabela de abreviações** em `configs/pares_treino_pxp.yaml` (23 palavras; cada forma observada nos produtos de treino com DF ≥ 5). Depois, rodar o `main()` regenera a parte A.

### F. Perguntas ainda sem resposta
- [ ] **F-pool.** Qual foi o tempo **real** do autor para anotar o pool? Os timestamps indicam ~2 h numa tarde (3/11); o texto de retomada falava em "semanas". As estimativas de esforço da B2 escalam com isso.
- [ ] **F-tail.** Como o P5 deve tratar os 13.085 pares da TAIL sem tamanho (não verificáveis): excluir, incluir com menor peso ou amostrar para revisão do autor?

---

## 9. O que o Claude faz a seguir (ordem sugerida)

> Nenhum destes depende das anotações do autor, exceto onde indicado. Cada bloco segue o ritmo: plano curto → RED → parada → GREEN.

1. **P5: pares da TAIL** (`pares_tail_pxp.parquet`, origens `tail_variante`, `tail_nf`, `tail_negativo`; ids `tail_<hash>`; mesmo formato `COLUNAS_PARES_TREINO_PXP`). **Propor o desenho antes de codar.** Pontos a decidir com o autor:
   - Montar `dados/brutos/tail/` a partir do clone com SHA-256 e commit `9d010ec` registrados (ADR-0013); a pasta não existe e fica no `.gitignore`.
   - **Partição por grupo de título original** (original, variantes e positivos ligados por union-find) **antes** de gerar negativos; assert de que nenhum grupo cai em duas partições.
   - **Checagem de quase-duplicatas** contra os 2.267 títulos do benchmark (não só exatos).
   - Filtro de tamanho: manter os 11.543 verificados; decisão sobre os 13.085 sem tamanho (pergunta F-tail).
   - Descartar `Fallback_Erro_LLM` e variantes idênticas ao original.
   - Negativos: reserva de títulos do `octaprice`; só com regra certa (tamanho diferente) ou aleatórios de baixo cosseno; nada de "negativo minerado" por similaridade sem regra.
   - Benchmark `pairs_to_label.csv` só como teste externo exploratório, nunca em treino ou validação; **golden test da spec 002 antes de qualquer número novo**.
   - Pesar a TAIL no treino (domínio Mercado Livre, 19 grupos de NF).
2. **P7: harness de avaliação e baselines** (specs 002 e 004, scripts 04 e 06). Harness único e **congelado antes de ler qualquer resultado do modelo**: Precision/Recall/F1, MRR, Recall@K, McNemar (ADR-0008), ponderação por `1/prob_inclusao` ou relato por estrato (o teste é estratificado), PR-AUC e reponderação na validação (prevalência de ~0,4% contra ~45% esperados no teste). Baselines: TF-IDF, BM25, Levenshtein, Jaccard, embeddings genéricos, LLaMA zero-shot. Dá para construir e testar com a validação; números de verdade só com o teste anotado.
3. **Ingestão do teste anotado** (`teste_pxp.parquet`, RF4/RF5): só depois de A1. `validar_anotacao_teste_pxp(..., completa=True)` já existe; falta o formato do arquivo e a adjudicação dos `incerto`.
4. **Reteste (T10c, plano 1.5.1):** sortear ≥ 150 pares com seed, emitir `anotacoes_teste_pxp_reteste.csv` sem rótulos e em nova ordem; depois calcular Kappa por tipo de par. Só depois de A1 + 7 dias.
5. **P6: script 05** (spec 003): verificação de VRAM (ADR-0009), formato do par, LoRA bf16 sem quantização, MLflow, **um YAML por adaptador**, smoke test em subconjunto. **Pré-requisitos do autor:** D1 a D4 e instalar o extra. Prioridade: adaptador p×p. O adaptador p×d continua bloqueado pela D-5.
6. **Fatia p×d:** `particionar_por_produto_canonico` (RF6), teste de 100 pares (A4), treino sem Generator (D-5).
7. **Higiene (com aval):** E1 a E3; ADR-0015 aceito; `main.tex`.

---

## 10. Armadilhas e lições (para não repetir)

- **`git add -A` é perigoso aqui:** as planilhas anotadas e o `proposta_tcc.docx` aparecem como novos. Nunca incluir sem o autor decidir (B3).
- **zsh:** `echo ======` falha (`= not found`); usar `printf '\n--- título\n'`. **macOS:** `sed -i ''` (com aspas vazias); padrões com `/` quebram o `sed`, usar Python.
- **ruff E501:** o `ruff format` **não** quebra docstrings nem f-strings; linhas > 100 colunas falham o `make lint`.
- **O shell volta ao diretório do projeto** entre comandos: usar caminhos absolutos ou `cd` explícito.
- **Contar pares únicos, não linhas direcionadas** do ranking (cada par mútuo aparece duas vezes).
- **Fixtures pequenas saturam:** os n-gramas de caracteres ligam qualquer produto a qualquer outro; por isso a integração da T12 usa um universo ampliado (24 produtos extras com vocabulário próprio).
- **Quando uma função grava artefatos, testar o "tudo ou nada"** (monkeypatch da etapa de verificação e checagem de que nada foi escrito).
- **Barreiras críticas devem rodar nos dados reais antes de confiar:** a de tamanho barrou 13 positivos de `pos_ordem` na primeira execução real.
- **O que o ranking `ranquear_entre_lojas` zera:** a mesma loja e o próprio produto. `ranquear_vizinhos` zera só o próprio produto (usa `lojas = arange(n)`).
- **Tolerância de cosseno:** vetores idênticos dão 0,9999999999999999; usar `_TOLERANCIA_COSSENO = 1e-9` nos cortes.
- **Parquet:** comparar DataFrames (`equals`), não bytes (metadado pode variar).
- **Make:** `make pipeline` roda 01→06 e **para no 04** (esqueleto); para rodar o que está pronto, `uv run python scripts/03_construcao_dataset.py` (ou `make construir-dataset`).
- **Dados da ALTA em exemplos:** nos documentos versionáveis, evitar descrições reais; nomes de marca e termos genéricos já aparecem em docs existentes.

---

## 11. Como verificar o estado e regenerar

### 11.1 P0 para a sessão nova
```bash
cd <raiz-do-repositorio>
git status --short                      # espera ~30 caminhos; nada commitado
git log --oneline -3                    # topo: dea0757 (nada novo commitado)
make check                              # espera 746 testes verdes
shasum -a 256 dados/processados/anotacoes_teste_pxp.csv dados/processados/anotacoes_treino_b2_pxp.csv
python3 - <<'PY'
import pandas as pd
for f in ["anotacoes_teste_pxp.csv", "anotacoes_treino_b2_pxp.csv"]:
    d = pd.read_csv(f"dados/processados/{f}", sep=";", dtype=str, keep_default_na=False)
    print(f, len(d), "linhas |", (d.rotulo != "").sum(), "anotadas |", d.rotulo.value_counts().to_dict())
PY
```
Os hashes só coincidem com a seção 5 se o autor **ainda não anotou nada**.

### 11.2 Regenerar tudo o que é regenerável
```bash
uv run python scripts/03_construcao_dataset.py   # ~12 s; idempotente; nunca reescreve planilhas do autor
```
Depois de editar `configs/pares_treino_pxp.yaml` (por exemplo a tabela de abreviações) ou de anotar mais da B2, basta rodar de novo: `pares_treino_auto_pxp.parquet` e `treino_pxp.parquet` são regenerados.

### 11.3 O que **não** se regenera
`anotacoes_teste_pxp.csv`, `anotacoes_treino_b2_pxp.csv`, `pool_cego/*.csv`, `pares_teste_pxp.csv`, `pares_b2_pxp.csv`, `anotacoes_amostra_cega.csv`. Os scripts lançam `FileExistsError` se tentarem reescrevê-los.

---

## 12. Erros meus corrigidos (transparência)

1. **Contagens de negativos infladas:** somei linhas direcionadas do ranking; os pares únicos de tamanho diferente são 91.916 (não 127 mil) e os difíceis (cosseno ≥ 0,5) 1.668 (não 3,3 mil). Corrigido no `design-treino-pxp.md` e na memória. Os 3.974 da B2 já eram únicos.
2. **Bug em `gravar_planilha_teste_pxp`:** ao generalizar a assinatura (`nome_arquivo`), esqueci de usar o parâmetro no corpo. Pego pelos testes, só em `tmp_path`.
3. **Positivos `pos_ordem` que mudavam o tamanho** (13 de 6.000; tamanho escrito com espaço, `750 ML`, `7/9 Kg`): pego pela barreira crítica na primeira execução real; corrigido com blocos de tamanho (`_blocos`) e rede de segurança `_preserva_tamanhos` nas quatro perturbações.
4. **Alocação inicial da parte A inviável** ([0,5, 0,7) só rende 3.099 com o teto de 3): a função falhou alto; ajustada para 3.000.
5. **Meus testes de integração da T12 usavam uma fixture que deixava o treino vazio:** troquei por um universo ampliado só nesses testes.
6. **Mineração automática de abreviações** tinha ~50% de lixo (`LATA→LACTEA`): descartada e trocada por tabela fechada.

---

## 13. O que não foi verificado

- **O ritmo real do autor** na anotação (seção 8, F-pool).
- **A precisão dos positivos da TAIL:** só o tamanho é verificável; a marca não. A taxa de ruído das variantes de LLM é desconhecida.
- **Se o adaptador aprende o atalho "mesmo tamanho ⇒ match":** a B2 é o contrapeso, mas só o teste (300 pares, ~45% de positivos) mede. A validação tem 25 `match` e mede mal.
- **`torch`/`peft` em Python 3.14 em runtime:** só o lock foi checado; nada foi instalado.
- **GPU e VRAM da Dharma-AI:** não confirmadas.
- **As 13.085 variantes da TAIL sem tamanho** e a checagem de quase-duplicatas contra o benchmark: o P5 ainda não começou.
- **A taxa de falsos negativos** nas anotações implícitas do pool (vazio = não-match) não foi medida.
