# Resultado da blocagem produto × dicionário (amostra cega)

**Projeto:** TCC — Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned
**Autor:** Pedro Henrique Medeiros Vieira
**Última atualização:** 2026-10-31
**Implementação:** `scripts/03_construcao_dataset.py` (`executar_blocagem`) — spec 001, RF1 "1a"; ADR-0006 (emenda de 2026-10-31)
**Config congelada:** `configs/blocagem.yaml` (TF-IDF, k = 20)  
**Fatia:** produto × dicionário (secundária desde o ADR-0014)
**Dados:** `dados/processados/anotacoes_amostra_cega.csv` (anotação), `resultados/metricas/recall_blocagem.csv` (recall), `latex/tcc_artigo/tabelas/tab_recall_blocagem.tex` (tabela do TCC, gerada pelo script 03)

---

## 1. Decisão

**Método: TF-IDF. k = 20.** Congelados antes de gerar os pares do teste (ADR-0006, emenda).

- **Método.** TF-IDF empata ou supera o BM25 em todos os k. A regra da emenda é escolher o de maior recall na amostra cega, e é o que foi aplicado. A diferença é de 1 a 3 produtos nos k pequenos, **não é evidência de superioridade**.
- **k.** O recall sobe de 45,2% (k=1) para 81,0% (k=5); a partir daí cada degrau vale 1 produto (k=10 e k=20), e os dois produtos extras de k=50 estão nos ranks 27 e 30. O custo de inferência do Cross-Encoder cresce linearmente com k (k=20 ≈ 4× k=5; k=50 ≈ 10×). Com 42 produtos, k=20 (85,7%) e k=50 (90,5%) não são estatisticamente distinguíveis. Alternativa considerada e não adotada: k=50, se sobrar orçamento de GPU.

## 2. Amostra e resultado

- 29.130 registros da base limpa → **28.240 textos normalizados distintos** (critério C2) → 50 sorteados com seed 42.
- 42 produtos com entrada no dicionário (denominador do recall), **8 `sem_entrada`** (16%), 0 `incerto`.

| k | TF-IDF | BM25 |
|---|---|---|
| 1 | 45,2% | 42,9% |
| 5 | 81,0% | 73,8% |
| 10 | 83,3% | 81,0% |
| 20 | **85,7%** | 83,3% |
| 50 | 90,5% | 90,5% |
| 100 | 90,5% | 90,5% |

Cada produto vale 2,4 pontos percentuais. A amostra é pequena e as diferenças entre métodos e entre k próximos são fracas como evidência.

## 3. O que os produtos não recuperados têm em comum

Quatro produtos (9,5% dos 42) não têm a entrada correta entre os 100 primeiros candidatos, nos dois métodos. O recall de 90,5% é, portanto, o **teto da blocagem lexical nesta amostra**; o Cross-Encoder não recupera esse limite sozinho (ADR-0006).

| Produto | Entrada anotada | Causa |
|---|---|---|
| `Composto Lácteo em Cápsula Nescau Nescafé Dolce Gusto Caixa 170g 10 Unidades` | `CAFE` | marca que embute a categoria (`NESCAFE` ⊃ `CAFE`) |
| `NESCAFE ORG EXTRA F SACHET 40G PROMO` | `CAFE` | idem |
| `Cerv.vold X Puro Malte S/gluten Lt.269ml` | `CERVEJA` | abreviação (`CERV`) |
| `Coxinha da Asa Empanada e Apimentada Fut Wings 700g` | `SOBRECOXA / COXA DE FRANGO / GALINHA` | vocabulário e morfologia (`COXINHA` ≠ `COXA`) |

**O que têm em comum:** nenhum compartilha um token inteiro (palavra) com a entrada. Os tokens são palavras, então marca que embute a categoria, abreviação e variação morfológica passam despercebidos. É o ruído de PDV que o TCC estuda (ver `notebooks/02_eda.ipynb`), e a falha é **de vocabulário, não de ranqueamento**: nenhum k a corrige.

**Cobertura sobre a base inteira.** Com TF-IDF e k=20, **1.959 dos 28.240 produtos distintos (6,9%) não têm nenhum candidato** (zero palavras em comum com o dicionário). Eles nunca chegam ao Cross-Encoder. Esse número é a contraparte, na base inteira, dos 9,5% da amostra.

## 4. Outros achados

- **Entradas de nome longo diluem o score.** Os 7 produtos recuperados só depois de k=5 (TF-IDF) têm entradas como `FEIJAO (PRETO, MULATINHO, ROXO, ROSINHA, ETC)`, `IOGURTE DE QUALQUER SABOR` e `DOCE DE BANANA EM PASTA`. O cosseno divide o score pelo tamanho do documento, e o `Feijao Branco Fibra 1kg` só aparece no rank 27.
- **Cobertura do dicionário.** 8 de 50 produtos (16%) não têm entrada que sirva (`sem_entrada`). Entram no TCC como limitação de cobertura do dicionário canônico, fora do cálculo do recall.
- **BM25 em corpus pequeno.** O `rank-bm25` zera o score de termos presentes em metade ou mais dos documentos; não afeta o dicionário real (1.593 entradas), mas explica por que as fixtures de teste precisam de mais de 2 entradas.

## 5. Limitações a declarar no texto

1. Amostra de 42 produtos com entrada, único anotador (sem segundo anotador, ADR-0005/0013).
2. Método e k escolhidos na própria amostra cega; não há outra amostra para medir o recall do ponto escolhido.
3. A blocagem usa tokens de palavra. Variantes que casariam as 4 falhas (n-gramas de caracteres, por exemplo) **não foram testadas**. Testá-las olhando esses 4 casos, na mesma amostra, inflaria o recall; se for feito, declarar a variante antes e medir em amostra nova.
4. O recall é medido sobre textos de um único dia de coleta (limitação L4 de `docs/limpeza_dados.md`).
