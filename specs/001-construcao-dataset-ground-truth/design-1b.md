# Design da 1.2b: blocagem produto × produto (entre lojas)

**Spec:** `requirements.md`, RF1 "1b" e CA-1b-01 a CA-1b-07 · **ADRs:** 0006, 0010, 0011, 0013, 0014
**Status:** proposta aprovada em 2026-10-31; T0 a T11 implementadas em 2026-11-13 (C0 a C10). A T12 (C11, integração e conjuntos derivados) está em andamento.

## 1. Visão geral

Quatro etapas idempotentes, no mesmo estilo de `executar_blocagem` (1a). Cada etapa só roda se a anterior deixou seu artefato, e nenhuma planilha de anotação é sobrescrita.

```
produtos_limpos.parquet
   │  C1 universo (texto, loja)
   ▼
[etapa 1] âncoras (permutação semeada) → C3/C4 rankings → C5 pool → planilha do lote N   (sem candidato rotulado)
   │                                                        ▲ autor anota, marca "âncora concluída"
[etapa 2] C6 valida anotação → C7 recall@k, acerto@k → resultados/metricas + tab_recall_blocagem_pxp.tex
   │                           regra de parada (Q2) só conta âncoras com positivo
   │      ── autor congela método e k em configs/blocagem_pxp.yaml ──
[etapa 3] C8 sorteio estratificado de 300 pares do teste (falha se método/k nulos)
[etapa 4] C9 componentes conexos (τ = 0,7) → partição (teste, validação = pool, treino = resto) → C10 vazamento residual
[etapa 5] C11 validacao_pxp.parquet (pares do pool na validação) e produtos_treino_pxp.parquet (só produtos)
```

**Onde fica o código:** em `scripts/03_construcao_dataset.py`, numa seção nova "Blocagem 1.2b", porque o pipeline tem um script por etapa e o 03 já concentra blocagem e partição. O arquivo passa de ~430 para ~900 linhas. A alternativa é um módulo auxiliar fora da numeração, que o `_carregar_script` do 03 importaria; escolho o 03 por coerência com a 1a e deixo o veto com o autor.

## 2. Reuso

| Já existe (1a) | Uso na 1b |
|---|---|
| `normalizar_texto`, `tokenizar` (via `_carregar_script`) | idem, sem duplicar |
| `deduplicar_por_texto_normalizado` | a lógica de id e representante é reaproveitada; a chave passa a ser (texto, loja) |
| `ranquear_tfidf`, `ranquear_bm25`, `_top_k` | não servem direto: o corpus é o próprio universo, precisa mascarar a mesma loja e o próprio produto. O padrão (lotes, desempate estável, score zero descartado) é copiado em `_top_k_entre_lojas` |
| `calcular_recall_por_k`, `montar_tabela_recall_tex` | o recall muda (por par, micro; acerto por âncora), mas a tabela `.tex` segue o mesmo formato |
| `carregar_config` | não é alterada: a 1b tem YAML próprio, para não quebrar a validação da 1a |
| `COLUNAS_MATCHER_ALTA` + assert ADR-0011 | aplicado a toda planilha e parquet novos |

## 3. Componentes e contratos

**C0. `configs/blocagem_pxp.yaml` + `carregar_config_pxp`.** Chaves: `seed`, `lote_ancoras`, `alvo_ancoras_com_positivo`, `max_ancoras`, `profundidade_pool` (100), `ngramas` ([3, 5]), `ks`, `metodo`/`k` (nulos até o congelamento), `tau_particao` (0,7), `n_teste` (300), `fracao_digito_divergente` (0,2), `faixas` e `n_por_faixa` (preenchidos depois do pool). Falha com `ValueError` se `metodo` ∉ {tfidf, bm25} (o n-grama nunca é oficial), se `k` ∉ `ks`, ou se só um dos dois estiver nulo.

**C1. `deduplicar_por_texto_e_loja(df) -> DataFrame`.** Colunas: `id_produto` (sha1 de texto normalizado + loja, 12 caracteres), `id_texto` (sha1 só do texto, igual ao `id_produto` da 1a, para cruzar com a 1a e responder Q1/Q3), `descricao`, `texto_normalizado`, `loja` (de `source`), `und_val`, `und_med`. Deve dar 28.921 linhas na base atual.

**C2. `tokens_numericos(texto) -> frozenset` e `divergencia_numerica(a, b) -> bool`.** Extrai números com unidade e normaliza (g/kg, ml/l, `,` decimal): 900 ML = 0,9 L. Diverge quando os dois lados têm tokens numéricos e os conjuntos diferem. Se algum lado não tem número, não diverge. É só critério de **seleção** de pares; nunca rotula.

**C3. `ranquear_entre_lojas(universo, metodo, k, ids_ancoras=None) -> DataFrame`** (com `ids_ancoras`, só esses produtos são consultas; o corpus continua sendo o universo todo) (`id_produto`, `id_candidato`, `metodo`, `rank`, `score`). TF-IDF e BM25. O candidato nunca é da loja do âncora nem o próprio âncora (assert, CA-1b-01). O vocabulário e o IDF vêm do universo inteiro: é estatística sem rótulo, mas o autor deve saber que o teste também entra nele.

**C4. `ranquear_ngramas(universo, ids, k)`.** TF-IDF `char_wb` 3–5 sobre o texto normalizado, **só para os âncoras** e só para formar o pool. Fica fora do dicionário `_RANQUEADORES`, e o config não aceita esse método.

**C5. `sortear_ancoras(universo, seed) -> DataFrame`, `montar_pool(ancoras, rankings, profundidade)` e `montar_planilha_pool(lote)`.**
- Uma permutação única do universo ordenado por `id_produto`; o lote N é o prefixo `[(N-1)*25 : N*25]`. Sem filtro de similaridade.
- O pool de cada âncora é a união dos três top-100, sem proveniência.
- Planilha: uma linha por (âncora, candidato), agrupada por âncora, candidatos em ordem alfabética do texto normalizado. Colunas (conferidas com a §5 do protocolo): `id_par`, `id_ancora`, `descricao_ancora`, `und_val_ancora`, `und_med_ancora`, `id_candidato`, `descricao_candidato`, `und_val_candidato`, `und_med_candidato`, `tipo_par` (`produto_produto`), `origem` (`amostra_cega`), `rotulo`, `ancora_concluida`, `observacao`, `timestamp_anotacao`. Sem a flag de teste-reteste da §5, que vale para a planilha do teste, não para o pool. Sem método, rank, score nem colunas do matcher ALTA (assert, CA-1b-02).
- Arquivo por lote, `dados/processados/pool_cego/lote_NN.csv`, nunca sobrescrito.

**C6. `validar_anotacao_pool(planilha)`.** Só forma. `rotulo` ∈ {vazio, `match`, `incerto`}; vazio em âncora concluída significa não-match. Âncora sem `ancora_concluida = sim` fica fora do recall e da contagem de parada. Falha por ids que não existem no pool ou rótulo fora do domínio. Nunca julga o mérito.

**C7. `calcular_recall_pxp(rankings, planilha, ks, metodos)`.** Por método e k: recall@k micro por par (positivos do pool no top-k do método ÷ positivos do pool), acerto@k por âncora. Positivo fora do top-100 do método conta como perda. Âncoras sem positivo, `incerto` e âncoras não concluídas são contados à parte. Grava `resultados/metricas/recall_blocagem_pxp.csv` e `tab_recall_blocagem_pxp.tex`.
- **Extensão proposta, que não está na spec:** IC 95% por bootstrap sobre âncoras (seed fixa). Com ~30 âncoras o IC é necessário para o texto do TCC. Precisa do seu aval antes de eu editar o CA-1b-03.

**C8. `sortear_pares_teste(candidatos, cfg, seed)`.** Candidatos: top-k do método congelado para todos os produtos, entre lojas, cada par uma vez. Estratos: faixas de score (`faixas`) mais dígito divergente (C2) com ~20% do teste. Cada produto em no máximo um par. Falha com `ValueError` se um estrato tiver menos candidatos que o alocado: não reduz em silêncio. Saída: `id_a`, `id_b`, `estrato`, `prob_inclusao`, sem rótulo.
- Faixas e alocação são decididas **depois** do pool anotado, a partir de `taxas_positivos_por_faixa(...)`, que só imprime as taxas. A escolha é gravada no YAML pelo autor.
- Consequência para a spec 004: o teste é estratificado, então métricas agregadas pedem ponderação pelo inverso de `prob_inclusao`, ou relato por estrato.

**C9. `componentes_conexos(universo, tau, arestas_extra) -> Series`, `particionar_componentes` e `verificar_particao_por_componente`.** Cosseno TF-IDF de palavras em lotes sobre todos os pares (inclusive mesma loja); `scipy.sparse.csgraph.connected_components` equivale ao union-find da spec; o rótulo do componente é o menor `id_produto` dele, então a saída não depende da ordem das linhas. As arestas extra ligam os dois produtos de cada par do teste. **Regra (decisão do autor, 2026-11-13, τ = 0,7 mantido):** o componente que toca o teste vai inteiro para o teste; o que toca o pool (e não o teste) vai inteiro para a validação; o restante é treino. Não há proporção 80/20 (a chave `proporcao_treino` é obsoleta e rejeitada): a validação é o que o pool toca. Medido na base real: teste 21,8% (6.312 produtos), validação 34,4% (9.953), treino 43,8% (12.656). Assert, como `AssertionError` explícito: nenhum componente em duas partições (CA-1b-06). Escolha do τ, para registro: em 0,8 sobrariam 52 `match` na validação e 57,9% de treino, mas o vazamento residual iria de 28,4% para 56,8%; o autor manteve 0,7 para proteger o teste.

**C10. `vazamento_residual(positivos, componentes) -> float`.** Fração dos pares positivos do pool cujos dois lados caem em componentes diferentes. É o limite do critério τ = 0,7, reportado: 23 de 81 (28,4%). Sem positivos, levanta `ValueError`.

**C11. Conjuntos derivados da partição (T12): `montar_validacao_pxp`, `montar_produtos_treino_pxp`, `gerar_conjuntos_pxp`.**
- `validacao_pxp.parquet`: pares do pool com os dois lados na validação, uma linha por par **não ordenado** (`id_a` < `id_b`; o mesmo par visto dos dois lados, como âncora de um e de outro, conta uma vez). Rótulo `match` ou `nao_match`: vazio em âncora concluída é `nao_match`, `incerto` fica de fora. O mesmo par com rótulos diferentes nos dois sentidos levanta `ValueError` com os ids (inconsistência que só o autor resolve). O rótulo é sempre o do autor, nunca a heurística.
- `produtos_treino_pxp.parquet`: só os produtos da partição de treino, sem par e sem rótulo. É a única entrada permitida para gerar pares de treino (P4), o que garante por construção que nenhum produto do teste ou da validação alimente a geração (ADR-0004). Os pares de treino (`treino.parquet`) dependem da supervisão distante e do desenho do P4, e não saem na T12.
- `gerar_conjuntos_pxp` calcula tudo antes de gravar (tudo ou nada), grava os cinco arquivos da partição e verifica por assert que nenhum produto do teste nem do pool está nos produtos de treino.

## 4. Modelos de dados

| Artefato | Chave | Observação |
|---|---|---|
| `pool_cego/lote_NN.csv` | (`id_ancora`, `id_candidato`) | o autor edita só `rotulo`, `ancora_concluida`, `observacao`, `timestamp_anotacao` |
| `pool_cego/ancoras_lote_NN.csv` | `id_ancora` | âncoras sorteadas do lote, inclusive as sem candidato (que não têm linha na planilha); sem ele a regra de parada não sabe quantas já foram sorteadas. Gravado junto com o lote, nunca sobrescrito |
| `resultados/metricas/recall_blocagem_pxp.csv` | (`metodo`, `k`) | mais `n_ancoras`, `n_com_positivo`, `n_incerto`, `n_nao_concluidas` |
| `pares_teste_pxp.csv` | (`id_a`, `id_b`) | sem rótulo; a anotação do teste é outra planilha |
| `componentes_pxp.parquet` | `id_produto` | `componente`, `particao` |
| `resultados/metricas/particao_pxp.csv` | `particao` | `n_componentes`, `n_produtos`, `fracao_base`, `maior_componente` |
| `resultados/metricas/vazamento_residual_pxp.csv` | `tau` | positivos do pool e separados, vazamento residual, pares, `match` e `incerto` da validação |
| `validacao_pxp.parquet` | (`id_a`, `id_b`) | pares do pool na validação, `rotulo` ∈ {match, nao_match} |
| `produtos_treino_pxp.parquet` | `id_produto` | produtos da partição de treino, com `componente` |

## 5. Regra de parada do pool (Q2, confirmada pelo autor em 2026-10-31)

1. Ordem fixa: a permutação semeada, em lotes de 25, sem filtro por similaridade.
2. Depois de cada lote concluído, contar só os âncoras com pelo menos um `match`. O recall **não** é calculado antes da parada, para não haver decisão olhando o resultado.
3. Parar quando houver **≥ 30 âncoras com positivo** ou ao chegar a **100 âncoras sorteados**, o que vier primeiro. No teto com menos de 30, reportar como está, com IC, sem sortear mais.
4. Âncora sorteado não é descartado nem substituído. Os sem positivo são resultado (cobertura de SKU compartilhado entre lojas), não falha.
5. Antes do lote 2, o autor pode reduzir o alvo ou o teto **por esforço** (nunca pelo recall), registrando a mudança no YAML e no log.

Por que não as alternativas: filtrar âncoras por similaridade alta, ou trocar âncoras sem positivo por outros, condiciona a amostra ao que a blocagem lexical acha fácil e infla o recall; parar olhando o recall é viés de parada.

Esforço: ~142 itens por âncora (mediana) → ~3.500 itens no lote 1 e até ~14.000 no teto. A taxa de âncoras com positivo ainda não é conhecida: a proxy medida dá **piso de 14,8%** (vizinho de outra loja com cosseno ≥ 0,9) e teto de 68,1% (cosseno ≥ 0,5). Com 14,8% o teto de 100 âncoras rende ~15 com positivo; com 30% ou mais, o alvo de 30 sai antes do teto.

## 6. Estratégia de erro (falha cedo, nunca engole)

| Cenário | Tratamento |
|---|---|
| Config inválida ou método/k nulo no sorteio do teste | `ValueError` com o caminho do YAML (CA-1b-04) |
| Coluna do matcher ALTA em planilha ou parquet | `assert` (ADR-0011) |
| Candidato da mesma loja que o âncora | `assert` (CA-1b-01) |
| Rótulo fora do domínio ou id fora do pool | `ValueError` com a lista dos ids |
| Planilha de lote já existente | `FileExistsError`; nunca sobrescreve (é onde o autor anota) |
| Estrato sem candidatos suficientes | `ValueError` informando o estrato e as contagens |
| Componente em duas partições | `assert` (CA-1b-06) |
| Âncora não concluída | não é erro: fica fora do cálculo e é contada |

## 7. Riscos e custos a medir

- **Tempo na base inteira (medido na T3, 2026-10-31, 28.921 produtos, 8 lojas):** TF-IDF com k=100 leva ~9 s (2,8 milhões de pares; 28.884 produtos com ao menos um candidato, 37 sem nenhum) e pico de ~1,2 GB de memória; BM25 leva ~9 ms por consulta, ≈ 4 min para a base inteira (extrapolado de 100 consultas). Os dois são viáveis; o sorteio do teste não depende de qual método for congelado.
- **CA-1b-07 (hash idêntico):** parquet pode variar por metadado entre versões; se acontecer, comparar o DataFrame em vez do arquivo e registrar.
- **Pares de texto idêntico entre lojas** (cosseno = 1) são triviais para qualquer baseline e podem dominar a faixa mais alta (Q7).

## 8. Perguntas abertas deste Design

| # | Pergunta | Dono | Bloqueia? |
|---|---|---|---|
| Q2 | Resolvida: regra da §5 confirmada (alvo 30, teto 100, lote 25) | autor | Não |
| Q7 | Pares com texto normalizado idêntico entre lojas entram no teste? Recomendo estrato próprio, pequeno, para não inflar a faixa alta | autor | Só o sorteio do teste |
| Q8 | Prevalência-alvo de positivos no teste (sugestão: algo entre 30% e 60%), decidida ao ver as taxas por faixa do pool | autor | Só o sorteio do teste |
| Q9 | **Resolvida em 2026-11-13:** sem proporção; validação = pool fora dos componentes do teste, treino = o restante, τ = 0,7 mantido | autor | Não |
| Q10 | IC por bootstrap em C7 (extensão do CA-1b-03) | autor | Não |
