# Design do P4: pares de treino produto × produto

**Spec:** `requirements.md`, RF2 e RF7 · **ADRs:** 0004, 0010, 0011, 0013, 0014
**Status:** o autor escolheu a opção **B2** em 2026-11-13 e aprovou a reescrita da RF2 (por **ADR-0015**, rascunho aguardando a revisão do texto) e a receita de perturbação da parte A (seção 5). **Implementados:** a B2 (planilha gerada), a parte A (14.200 pares) e a montagem do `treino_pxp.parquet` (seção 10), que já lê qualquer quantidade de anotação B2. **P5 (TAIL) implementado em 2026-11-16** (`gerar_pares_tail_pxp`, 23.758 pares, D1 a D6 em `configs/pares_tail_pxp.yaml`); **falta** a anotação da B2 pelo autor.

## 1. A pergunta

A RF2 pede supervisão distante: "pares com correspondência de marca + unidade normalizada recebem rótulo provisório automático". A base não tem coluna de marca. Dá para extrair a marca do texto, e com que ruído?

## 2. Como foi medido

Investigação só de leitura, em 2026-11-13, sobre os 12.656 produtos de `produtos_treino_pxp.parquet`. O ruído das regras foi medido contra o rótulo do autor nos 5.906 pares de `validacao_pxp.parquet` (25 `match`). Esse uso é só para medir e reportar: nenhuma regra foi ajustada olhando a validação. Os scripts de medição ficaram no scratchpad da sessão e não estão versionados; se o desenho for aprovado, a medição de ruído vira script ou teste versionado, porque o número entra no texto do TCC.

## 3. O que a medição mostra

| Achado | Número |
|---|---|
| Tamanho extraído do texto concorda com a coluna de unidade da loja (onde ambos existem) | 11.279 de 11.280 (99,99%) |
| Texto com tamanho reconhecível (g, kg, ml, l) | 89,1% dos produtos de treino |
| Os 25 `match` do autor têm o mesmo tamanho; entre os `nao_match`, o mesmo tamanho ocorre em | 25,8% |
| **Tamanho diferente como regra de não-match:** corretos | **3.283 de 3.283** |
| Regra "mesmo tamanho + ao menos 1 token de marca em comum" (léxico automático, 1.673 tokens) | dispara em 350 pares, 11 são `match`: **precisão 3,1%**, recall 44% |
| Regra "mesmo tamanho + cosseno TF-IDF ≥ 0,7" | dispara em 51, 8 são `match`: precisão 15,7%, recall 32% |
| Regra "só mesmo tamanho" | dispara em 1.550, os 25 são `match`: precisão 1,6% |
| Textos normalizados idênticos entre 2+ lojas no treino | 94 textos (na validação, só 1 par: não dá para estimar a precisão) |

Por que a marca não resolve: o léxico automático mistura marcas (SEARA, SADIA, YOKI), embalagens (PACOTE, CAIXA), descritores (PREMIUM, ORGANICO) e castas de vinho (MALBEC, CABERNET), e a TAIL não ajuda porque suas marcas são de e-commerce (relógios, geladeiras). Mas o problema é mais fundo: mesmo com marca perfeita, **marca + tamanho** iguais ainda juntam produtos diferentes da mesma marca (empanado e salsicha Perdigão de 100 g) e variantes (sabores). A decisão de marca e variante só é segura com o rótulo do autor.

**Consequência:** na ALTA existe um rótulo **certo** para negativos (tamanho diferente) e nenhum para positivos. A RF2 precisa ser reescrita, e o texto da RF2 e a menção a "supervisão distante" no ADR-0004 pedem a sua decisão.

## 4. Opções

| | O que é | Prós | Contras |
|---|---|---|---|
| **A** (recomendada como base) | Só rótulos certos. **Negativos:** pares entre lojas com tamanho diferente. **Positivos:** o texto do próprio produto perturbado (unidade 900ML ↔ 0,9L, inversão de ordem, abreviação e ruído tipográfico; RF7), mais os pares de variantes da TAIL (P5). | Sem custo de anotação, sem LLM, rótulo certo por construção, executável já. 91.916 negativos únicos disponíveis (top-20 entre lojas), só 1.668 deles difíceis (cos ≥ 0,5). | Não ensina marca nem variante no domínio. **Risco de atalho:** positivos e negativos concordam em "mesmo tamanho ⇒ match", e o teste mora justamente nos 56.731 pares únicos de mesmo tamanho. Os positivos perturbados são menos variados que os reais. |
| **B** | A + anotação sua em pares do **treino**, estilo pool (âncoras do treino, candidatos em ordem alfabética, vazio = não-match). | Ensina marca e variante no domínio com rótulo de verdade. | Custo seu: o pool de 75 âncoras rendeu 81 positivos e 11 mil julgamentos. Dá para fazer em escala menor (por exemplo 25 âncoras). Fora do plano atual. |
| **C** | A + rótulo de LLM **só no treino**, com o ruído medido na validação. | Cobre a região de mesmo tamanho. | Depende do D-5 (Generator suspenso) e da autorização da Dharma-AI (C1 das pendências). Circularidade com o baseline LLaMA zero-shot. Exige ADR novo (emenda do 0004 e do 0013). Só 25 positivos na validação para estimar o ruído. |
| **D** | Manter a RF2 (marca + tamanho). | Nenhum. | **Descartada pelos números:** 96,9% dos "positivos" seriam falsos. |

**Recomendação:** começar pela **A** (zero custo seu, destrava o script 05 e o treino) e decidir **B** depois de olhar o perfil de erro do adaptador na validação, mas a decisão tem prazo: se for B, a anotação precisa começar cedo. A **C** só se você retomar o D-5.

## 5. Desenho da opção A (receita aprovada pelo autor em 2026-11-13)

- **Entrada única:** `produtos_treino_pxp.parquet`. Assert: nenhum id de par fora dele (ADR-0004). Config versionada nova, `configs/pares_treino_pxp.yaml`, com seed, razão positivo:negativo, faixas de cosseno e tetos por loja.
- **Negativos seguros:** top-20 TF-IDF entre lojas (o mesmo `ranquear_entre_lojas`), só pares com tamanho nos dois lados e **diferente** (via `tokens_numericos`). Amostragem estratificada por faixa de cosseno ([0,0.3), [0.3,0.5), [0.5,0.7), [0.7,1]) para os difíceis não ficarem diluídos. Teto por produto e por par de lojas: a Extra e a Guedes somam 65% do treino.
- **Positivos por perturbação (RF7):** unidade (via normalização de tamanho), inversão parcial de ordem, abreviação e ruído tipográfico que preservem marca e tamanho. Cada positivo é o produto contra a sua própria versão perturbada. Aplicados só depois da partição, só ao treino.
- **Positivo opcional:** texto normalizado idêntico entre lojas (94 textos), marcado em `origem` à parte, até medirmos a precisão.
- **Saída:** `treino_pxp.parquet` (o par do `validacao_pxp.parquet`; o adaptador produto × dicionário terá o seu) com as colunas da `validacao_pxp.parquet` mais `origem` fina (`neg_tamanho`, `pos_unidade`, `pos_ordem`, `pos_abrev`, ...), para a ablação e para auditar o ruído.
- **Sem rótulo de LLM, sem `codg_item`/`desc_ref`/`match_score`, sem heurística de marca.** Pares sem tamanho num dos lados não recebem rótulo (31.390 pares únicos no top-20): ficam de fora.
- **Testes (3 camadas):** nenhum negativo com tamanho igual; nenhum positivo que mude o conjunto de tamanhos; determinismo por seed; nenhum id fora do treino; sem colunas da ALTA.

## 6. Riscos que o autor assume na opção A

- O adaptador pode aprender "mesmo tamanho ⇒ match". A validação tem só 25 positivos para detectar isso; o teste (300 pares, ~45% de positivos) é que mede. Plano de reação: a opção B.
- O treino teria poucos positivos "reais" (só os da TAIL, de outro domínio). A limitação deve entrar no texto do TCC.

## 7. Perguntas ao autor (respondidas em 2026-11-13: 1 = B2; 2 = sim, por ADR-0015; 3 = sim)

1. Opção A como base? E B (anotação em âncoras do treino) fica prevista, adiada ou descartada?
2. Aprova reescrever a RF2 (e o trecho de supervisão distante do ADR-0004) com este desenho? A mudança de decisão registrada em ADR pede ADR novo, sem reabrir o 0004.
3. Aprova a receita de perturbação da seção 5, em especial a abreviação?

## 8. Decisão do autor e desenho da B2 (2026-11-13)

**Decisão:** opção B2. O autor anota, no treino, os pares entre lojas com **mesmo tamanho e cosseno TF-IDF ≥ 0,5**, em cima da parte A (negativos por tamanho diferente, positivos por perturbação, TAIL).

- **Seleção.** Top-20 TF-IDF entre lojas **dentro** de `produtos_treino_pxp.parquet` (vocabulário e IDF só do treino), pares com tamanho reconhecível e igual nos dois lados (`tokens_numericos`) e cosseno ≥ `b2_cosseno_minimo` (0,5, em `configs/blocagem_pxp.yaml`), um por par não ordenado. Medido: **3.974 pares** entre 3.072 produtos (por faixa de cosseno: 1.648 em [0,5; 0,6), 930 em [0,6; 0,7), 1.013 em [0,7; 0,9), 383 em [0,9; 1]). Os pares são congelados em `pares_b2_pxp.csv`, uma única vez.
- **Formato: cartão por par, rótulo explícito nos dois sentidos** (`match`, `nao_match`, `incerto`), em ordem embaralhada com seed, na **mesma planilha e com a mesma ferramenta do teste** (`anotador_teste.html`). Arquivo `dados/processados/anotacoes_treino_b2_pxp.csv`, `origem = treino_b2`, nunca sobrescrito. A lista por âncora, como no pool, foi descartada: a atribuição hub-first dá 1.546 âncoras com mediana de 2 pares (44% com um só), então o ganho da lista longa desaparece, e o vazio como não-match esconderia falsos negativos por omissão numa faixa com 7% a 11% de positivos.
- **Uso dos rótulos.** `incerto` fica fora. `match` e `nao_match` entram em `treino_pxp.parquet` com `origem = autor_b2`. Não há reteste (não é teste).
- **Isolamento.** Só ids de `produtos_treino_pxp.parquet`, com assert: nenhum produto do teste, do pool ou da validação.
- **Limite.** O corte por cosseno perde cerca de 8% dos positivos (na validação, 23 de 25 ficam acima de 0,5), justamente os de menor similaridade lexical; a perturbação por abreviação da parte A cobre esse caso.
- **Esforço estimado:** 1,5 a 5,5 h; ~430 positivos (extrapolado de 25 `match` da validação, então ordem de grandeza).

### Correção de contagem (2026-11-13)

As contagens da seção 3 e da tabela da seção 4 que citavam "127 mil", "3,3 mil", "79 mil" e "42 mil" somavam linhas direcionadas do ranking, e cada par mútuo aparecia duas vezes. Os números corretos, em pares **únicos**, para o top-20 TF-IDF entre lojas no treino: 180.037 pares, dos quais 91.916 de tamanho diferente, 56.731 de mesmo tamanho e 31.390 com algum lado sem tamanho. Negativos por tamanho por faixa de cosseno: [0, 0,2) 37.584; [0,2, 0,3) 37.863; [0,3, 0,5) 14.801; [0,5, 0,7) 1.500; [0,7, 1] 168. Os difíceis (≥ 0,5) saturam em 1.668 pares (1.742 produtos) e não crescem com k maior (testado até 100). Os 3.974 pares da B2 já eram únicos. **Extensão em aberto:** dentro da mesma loja há mais 3.932 pares únicos de tamanho diferente com cosseno ≥ 0,5 (730 com ≥ 0,7); a receita aprovada usa só pares entre lojas, e incluir os da mesma loja é decisão do autor.

## 9. Parte A implementada (2026-11-13)

**Decisões do autor em 2026-11-13:** incluir os negativos da **mesma loja** (`incluir_mesma_loja: true`, +3.932 pares difíceis) e usar uma **tabela fechada de abreviações**, revisável no YAML. A mineração automática de abreviações foi descartada (metade saiu lixo, por exemplo `LATA→LACTEA`).

**Na base real** (`configs/pares_treino_pxp.yaml`, seed 42): 14.200 pares em `pares_treino_auto_pxp.parquet`, gerados em ~3 s, deterministicamente. Negativos 8.200 (alocação [0,0-0,3) 1.500; [0,3-0,5) 3.000; [0,5-0,7) 3.000; [0,7-1,0] 700), dos quais 5.107 (62%) da mesma loja. Positivos 6.000, um por produto: ordem 2.116, ruído 1.978, unidade 1.333, abreviação 573. Disponibilidade com a mesma loja incluída (pares únicos, k = 20): [0,0-0,3) 47.322; [0,3-0,5) 31.973; [0,5-0,7) 4.657 (3.099 com o teto de 3 pares por produto); [0,7-1,0] 898. As contagens da config são valores iniciais, ajustáveis, e a função falha nomeando a faixa se pedirem mais do que existe.

**A barreira crítica funcionou.** Na primeira execução real, `verificar_pares_treino_auto` barrou 13 positivos de `pos_ordem` (de 6.000) que mudavam o conjunto de tamanhos: tamanhos escritos com espaço (`750 ML`, `7/9 Kg`) são dois tokens, e a troca de lugar os separava. Corrigido (a ordem passou a mover blocos de tamanho inteiros), coberto por teste, e as quatro perturbações ganharam uma rede de segurança que devolve `None` se o tamanho mudar.

**Para o autor notar:**
- Os negativos da mesma loja dominam (62%) porque é onde está a maioria dos difíceis; o teste é só entre lojas. `incluir_mesma_loja: false` volta ao desenho original (só 1.668 difíceis).
- Os positivos por perturbação são fáceis e só `pos_abreviacao` depende da tabela: 573 de 6.000 (9,6%).
- A fonte `autor_b2` (a sua anotação) e a TAIL entram no `treino_pxp.parquet` na montagem final (seção 10).

## 10. Medição da TAIL e montagem do `treino_pxp.parquet` (2026-11-13)

**O clone da TAIL** (`invoice-data-normalizer/`, commit `9d010ec`, uso só local) tem mais dado do que a primeira inspeção sugeria. Medido, só de leitura; todos os títulos do benchmark (2.267 títulos distintos nos 1.200 pares de `pairs_to_label.csv`) são proibidos no treino e na validação, e nenhum aparece nos arquivos abaixo por correspondência exata (a checagem de quase-duplicatas é parte do P5):

| Arquivo | O que é | Volume | Uso |
|---|---|---|---|
| `old_attack_dataset.csv` | par (título original, variante gerada por LLM), sem tipo | 43.047 linhas, 9.610 originais, até 3 variantes cada; 16.120 variantes iguais ao original (descartadas) → **26.927 pares únicos** | positivos `tail_variante` |
| mesmos pares, filtro de tamanho | só 51,4% dos originais têm tamanho reconhecível; desses, **83,4% das variantes preservam o conjunto de tamanhos** (11.543 pares) e 16,6% o corrompem (unidade trocada por letra errada ou tamanho cortado) | 11.543 verificados; 13.085 sem tamanho, não verificáveis | os verificados entram; os não verificáveis são decisão do P5 |
| `attack.csv` | 100 originais com variante tipada | 601 linhas: erro de digitação 171, abreviação 170, notação de unidade 170, `Fallback_Erro_LLM` 90 (falha do LLM, descartar) | positivos com tipo, auditáveis |
| `itens_nf_normalizados.csv` (= `train_supervised` 152 + `test_supervised` 38) | itens de nota fiscal de supermercado agrupados pelo mesmo nome normalizado (títulos abreviados, com variação de unidade e com erro de digitação do mesmo produto) | 190 títulos em **19 grupos** → 855 pares positivos | positivos `tail_nf` (ruído real de PDV, mas só 19 produtos) |
| `octaprice_mercadolivre_1/2.json` | avaliações com a URL do anúncio (o título está no slug) | 18.084 URLs → 17.415 títulos distintos | só como reserva de negativos; não traz par nem rótulo |
| `AmostraDescMerc.csv` | descrições de NF-e com categoria | 15.000 linhas | sem pares |

**Ressalvas:** as variantes foram geradas por LLM e podem alterar marca (que não dá para verificar); o domínio é Mercado Livre (cosméticos e capilares nos exemplos), não supermercado; os 19 grupos de NF são de domínio próximo mas pouquíssimo diversos. Os `normalized` de `train_supervised` e `itens_nf_normalizados` são dados de referência da TAIL, não predições dos modelos avaliados por ela (ADR-0013, item 7). O partição por grupo de título original e a construção dos pares (`pares_tail_pxp.parquet`) são o P5; a montagem abaixo só consome o que o P5 entregar.

**Montagem (`gerar_treino_pxp`).** Junta, no formato de pares de `validacao_pxp.parquet`: (a) `pares_treino_auto_pxp.parquet` (obrigatório); (b) as anotações B2 que já existirem em `anotacoes_treino_b2_pxp.csv` (só `match` e `nao_match`; como a planilha é embaralhada com seed, qualquer subconjunto anotado é uma amostra sem viés de estrato); (c) `pares_tail_pxp.parquet`, se existir. Tudo ou nada, regenerável, sem nunca escrever na planilha do autor. A barreira `verificar_treino_pxp` exige: ids reais só de `produtos_treino_pxp`; lado sintético com prefixo `sint_` (perturbação) ou `tail_` (TAIL, nunca igual a um id real); B2 e negativos com tamanho igual/diferente conforme a origem; positivos que preservam o tamanho; rótulo só `match` ou `nao_match`; `id_par` único entre fontes; nenhuma coluna da ALTA. Resumo em `resultados/metricas/treino_pxp_resumo.csv`.
