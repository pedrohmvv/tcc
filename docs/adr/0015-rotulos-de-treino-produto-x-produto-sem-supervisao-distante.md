# ADR-0015: Rótulos de treino produto × produto sem supervisão distante por marca e tamanho

**Status:** **Proposto** (rascunho de 2026-11-13). O autor aprovou a direção em 2026-11-13 (reescrever a RF2 por ADR novo, a opção B2 e a receita de perturbação) e ainda precisa revisar este texto. **Emenda o ADR-0004 apenas no item "Treino"** (a supervisão distante). Não altera o resto do ADR-0004 (teste manual e independente, proibição de gerador ou LLM rotular teste ou validação, partição antes de qualquer geração), nem os ADRs 0010 e 0011 (as colunas do matcher ALTA continuam proibidas). Complementa os ADRs 0013 e 0014.

## Contexto
A RF2 da spec 001 e o ADR-0004 previam **supervisão distante**: pares cuja marca e cuja unidade normalizada coincidem recebem um rótulo provisório automático. A base não tem coluna de marca, só o texto, e a TAIL não ajuda: suas marcas, geradas por LLM, são de e-commerce (relógios, geladeiras), não de supermercado.

A viabilidade foi medida em 2026-11-13, em investigação só de leitura sobre os 12.656 produtos de treino e os 5.906 pares da validação. O rótulo do autor na validação serviu só para medir o ruído; nenhuma regra foi ajustada olhando para ele.

| Medida | Resultado |
|---|---|
| Tamanho extraído do texto × coluna de unidade da loja, onde ambos existem | concordam em 11.279 de 11.280 (99,99%) |
| Pares de **tamanho diferente** (ambos com tamanho) que são `match` | 0 de 3.283 |
| Regra "mesmo tamanho + token de marca em comum" (léxico automático de 1.673 tokens) | dispara em 350 pares, 11 são `match`: **precisão 3,1%**, recall 44% |
| Regra "mesmo tamanho + cosseno TF-IDF ≥ 0,7" | precisão 15,7%, recall 32% |
| Regra "só mesmo tamanho" | precisão 1,6%, recall 100% |

Mesmo com uma marca perfeita, marca e tamanho iguais continuam juntando produtos diferentes da mesma marca e variantes (sabores, categorias). Na ALTA existe, portanto, **rótulo certo para negativos** (tamanho diferente, protocolo §3.4) e **nenhum para positivos**.

## Decisão
1. A regra "marca + unidade normalizada ⇒ match provisório" é abandonada. Nenhum rótulo de treino produto × produto é derivado de marca extraída do texto.
2. Os rótulos de treino produto × produto vêm de quatro fontes, sempre dentro da partição de treino e identificadas na coluna `origem`:
   - **Negativos por tamanho diferente (`neg_tamanho`).** Pares com tamanho reconhecível e diferente nos dois lados, entre lojas e também da mesma loja (decisão do autor, 2026-11-13: dobra e meia os negativos difíceis), amostrados por faixa de cosseno para os difíceis não ficarem diluídos, com teto de pares por produto. `incluir_mesma_loja` no YAML liga e desliga a mesma loja.
   - **Positivos por perturbação do próprio texto (`pos_*`, RF7).** Unidade (900ML ↔ 0,9L), inversão parcial de ordem, abreviação e ruído tipográfico, sempre preservando marca e tamanho. Receita aprovada pelo autor em 2026-11-13.
   - **Anotação do autor, opção B2 (`autor_b2`).** O autor rotula os pares do treino com mesmo tamanho e cosseno TF-IDF ≥ `b2_cosseno_minimo` (0,5; 3.974 pares). Rótulos `match`, `nao_match` e `incerto`; o `incerto` fica fora.
   - **Pares da TAIL (ADR-0013).** Positivos de variantes do mesmo título e negativos minerados, com partição por grupo de título antes de gerar.
3. **Nenhum LLM ou gerador rotula ou gera pares produto × produto de treino enquanto o D-5 estiver suspenso.** A alternativa de rótulos de LLM só no treino não é adotada aqui; só por ADR novo. A proibição para teste e validação não muda.
4. A validação continua sendo exclusivamente o pool anotado pelo autor. Os rótulos da B2 ficam na partição de treino: a partição por componente conexo acontece antes de tudo, e as planilhas só contêm produtos da partição de treino.
5. Pares sem tamanho reconhecível em um dos lados não recebem rótulo automático.

## Consequências
- **Custo do autor:** a anotação da B2, estimada em 1,5 a 5,5 h (ritmo medido nos timestamps do pool) e ~430 positivos esperados (extrapolado de 25 `match`, ordem de grandeza).
- **Risco de atalho.** As fontes automáticas concordam em "mesmo tamanho ⇒ match", e a região de mesmo tamanho é onde o teste mora. A B2 é o contrapeso e o teste é o árbitro. Plano de reação: ampliar a B2 (com cosseno ≥ 0,4 seriam 6.997 pares).
- **Limite do corte por cosseno:** perde cerca de 8% dos positivos (na validação, 23 de 25 ficam acima de 0,5), justamente os de menor similaridade lexical. A perturbação por abreviação cobre parte desse caso.
- **Limitações a declarar no TCC:** positivos perturbados são menos variados que os reais; os pares da TAIL são de outro domínio; a validação tem só 25 `match` e mede mal o ganho. A coluna `origem` permite ablação por fonte.
- **Documentos a sincronizar, com o aval do autor:** o `main.tex` (§4, que cita "supervisão distante" entre os mecanismos de treino), o ADR-0011 (a linha de metadado de unidade cita a RF2; o papel de metadado do par continua) e o plano de desenvolvimento.
- **Produto × dicionário não é afetado:** continua dependendo do D-5.
- **Reversível:** se o D-5 for retomado, um ADR novo pode acrescentar rótulos de LLM como fonte adicional, medindo o ruído e arbitrando no teste.

## Alternativas consideradas
- **Manter a RF2 (marca + tamanho):** descartada, 96,9% dos positivos automáticos seriam falsos.
- **Cosseno + tamanho como regra de rótulo:** descartada, precisão de 15,7%.
- **Só os rótulos certos, sem anotação (opção A pura):** viável, mas deixa a decisão de marca e variante sem nenhum rótulo no domínio.
- **Anotação por âncoras do treino (B1):** menos densa; os 3.974 pares da B2 formam grupos pequenos (mediana de 2 pares por âncora), e o vazio como não-match esconderia falsos negativos.
- **Corte de cosseno em 0,4 (B3):** mais 3.023 pares por cerca de 14% a mais de positivos esperados; fica como plano de reação.
- **Rótulos de LLM só no treino:** dependem do D-5 e da autorização da Dharma-AI, têm risco de circularidade com os baselines e só 25 positivos para medir o ruído.
