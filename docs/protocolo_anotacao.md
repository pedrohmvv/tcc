# Protocolo de Anotação — Entity Matching de Produtos de Supermercado

**Projeto:** TCC — Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned
**Autor:** Pedro Henrique Medeiros Vieira
**Última atualização:** 2026-10-31
**Status:** regras **separadas por tipo de par** (ADR-0013): produto × dicionário decide categoria e variante; produto × produto decide SKU, com marca e tamanho. Rascunho da tarefa 1.3 do plano de desenvolvimento, **ainda não validado com o orientador**. Sem pendências de regra na Seção 3 (kit/promoção e marca própria decididos em 2026-10-31; marca própria só é reconhecida quando o texto declara). Falta a validação do orientador e a sincronização da skill `protocolo-anotacao-em`. **ADR-0014:** produto × produto é a fatia principal e produto × entrada canônica a secundária; os tamanhos de cada fatia estão em aberto.

---

## 1. Objetivo

Este documento define as regras operacionais que o anotador (autor) segue para decidir se um par de descrições de produto é `match` ou `não-match`, garantindo que decisões sejam **consistentes, reprodutíveis e auditáveis** — condição necessária para que o teste-reteste (Seção 4.1 da proposta) seja informativo.

## 2. Escopo dos pares anotados

Dois tipos de par são anotados no mesmo esforço, **com regras de decisão diferentes** (Seção 3):

1. **Produto × Entrada canônica** (fatia secundária, ADR-0014; tamanho a definir, menor que os ~250–450 originais) — par entre uma descrição bruta da base ALTA e uma entrada do dicionário canônico. A entrada canônica é um produto genérico, sem marca e sem tamanho (ex.: `ARROZ BRANCO`, `ARROZ INTEGRAL`).
2. **Produto × Produto** (fatia principal, ADR-0014; tamanho a definir, decisão D-13 — os ~50–100 originais provavelmente não bastam) — par entre duas descrições brutas de lojas diferentes, sem intermediação do dicionário. É o único tipo de par comparável ao benchmark da TAIL, que usa a mesma regra de SKU.

**Cada par é anotado sob a regra do seu tipo.** Uma regra não é aplicada ao outro tipo de par, e o tipo de par é registrado em cada linha (Seção 5).

### 2.1 Amostra cega (para medir o recall da blocagem)

Além dos pares acima, o autor anota ~50 **produtos** sorteados (seed fixa, deduplicados por texto normalizado), vendo **só o produto**, sem lista de candidatos e sem colunas do matcher ALTA. Para cada produto o autor procura no dicionário completo e registra a entrada correta, ou `sem_entrada` se nenhuma serve. Isso permite calcular o recall da blocagem sem o viés de só anotar o que ela devolveu (ADR-0006, emenda de 2026-10-31).

- A escolha da entrada segue a regra de produto × dicionário (Seção 3): categoria e variante; marca própria e kit/promoção não casam com entrada genérica.
- `[DECISÃO PENDENTE]` Se os pares (produto, entrada indicada) da amostra cega entram também no conjunto de teste como *match*. Recomendado: sim, porque são independentes da blocagem; precisa ser decidido antes de sortear o teste, para esses produtos não serem sorteados duas vezes.

## 3. Regras de decisão (match / não-match / incerto)

### 3.1 Regra geral, por tipo de par

| Tipo de par | É **match** se... |
|---|---|
| Produto × entrada canônica | o produto pertence ao produto genérico da entrada: **mesma categoria e mesma variante**. Marca e tamanho **não** decidem, com duas exceções de não-match: marca própria e kit/promoção (Seção 3.3). |
| Produto × produto | os dois são o **mesmo SKU**: mesma composição, **mesma marca**, mesma variante e **mesmo tamanho/quantidade**. |

**Consequência:** dois produtos que casam com a mesma entrada canônica são da **mesma categoria**, não necessariamente o mesmo produto. "Arroz marca X 1 kg" e "arroz marca Y 5 kg" casam ambos com `ARROZ BRANCO`, mas são SKUs diferentes (ADR-0013, que emenda o ADR-0007).

### 3.2 Casos de MATCH

Valem para **os dois tipos de par**, dentro da regra do tipo:

| Situação | Exemplo (ilustrativo) | Decisão |
|---|---|---|
| Abreviação/truncamento sem mudança semântica | "LEITE INTEGRAL ITALAC 1L" vs. "LT ITALAC INTEGRAL 1000ML" (produto × produto) | **match** |
| Inversão na ordem dos tokens | "OLEO SOJA LIZA 900ML" vs. "OLEO COMP SOJA LIZA 0,9L" (produto × produto) | **match** |
| Ruído tipográfico de PDV (letras faltando, sem acento) | "BISCOITO MARIA BAUDUCCO 200G" vs. "BISC M BAUDUCCO 200GR" (produto × produto) | **match** |
| Unidade equivalente expressa de forma diferente, **só em produto × produto** | "0,9L" vs. "900ML" (equivalência numérica exata) | **match** |

Em produto × entrada canônica, a equivalência de unidade não decide nada (o tamanho não conta); o que decide é a categoria e a variante.

### 3.3 Casos de NÃO-MATCH

**Produto × entrada canônica** (decide categoria e variante):

| Situação | Exemplo (ilustrativo) | Decisão |
|---|---|---|
| Variante diferente da entrada | produto "ARROZ INTEGRAL ..." vs. entrada `ARROZ BRANCO` | **não-match** |
| Categoria diferente da entrada | produto de arroz vs. entrada de feijão | **não-match** |
| Kit/promoção vs. entrada | produto "LEVE 3 PAGUE 2 ARROZ ..." vs. `ARROZ BRANCO` | **não-match** — unidade de compra diferente (decisão do autor, 2026-10-31) |
| Marca própria (private label) | produto de marca própria vs. entrada genérica | **não-match** (decisão do autor, 2026-10-31). É a **única** exceção à regra "marca não decide" nesta fatia. **Critério de reconhecimento (decisão do autor, 2026-10-31):** o produto é de marca própria **somente quando o texto da descrição declara** (ex.: "[MARCA PRÓPRIA]" ou expressão equivalente escrita na descrição). O conhecimento do anotador sobre as marcas das redes **não** é usado. Marca própria sem sinal no texto é rotulada pelas regras gerais (em geral, match por categoria e variante); isso é uma limitação conhecida e deve ser declarada no TCC. |

**Produto × produto** (decide SKU):

| Situação | Exemplo (ilustrativo) | Decisão |
|---|---|---|
| Mesma marca, variante de composição diferente | "LEITE ITALAC INTEGRAL 1L" vs. "LEITE ITALAC DESNATADO 1L" | **não-match** |
| Marca diferente, incluindo marca própria vs. marca nacional | "LEITE TIPO A [MARCA PRÓPRIA] 1L" vs. "LEITE ITALAC 1L" | **não-match** — produtos distintos, mesmo se funcionalmente similares |
| Tamanho/unidade diferente | "LEITE ITALAC 500ML" vs. "LEITE ITALAC 1L" | **não-match** |
| Kit/promoção vs. unidade avulsa | "LEVE 3 PAGUE 2 BISCOITO X" vs. "BISCOITO X 200G" | **não-match** — unidade de compra diferente |
| Mesma marca, categoria de produto diferente | "ITALAC LEITE 1L" vs. "ITALAC IOGURTE 170G" | **não-match** |

### 3.4 Tamanho e unidade

- **Produto × entrada canônica:** o tamanho **não** afeta a decisão (a entrada não tem tamanho).
- **Produto × produto:** o tamanho **afeta** a decisão (1 kg ≠ 5 kg).
- Nos dois tipos de par, tamanho/unidade continua sendo registrado como **metadado** (Seção 5), porque é relevante para caracterizar o ruído de PDV.

Não há mais pendência sobre a granularidade do dicionário: ela foi confirmada por inspeção direta do arquivo (`dados/brutos/dicionario_canonico.csv`, 1.593 entradas de dados) e a decisão por tipo de par está registrada no ADR-0013.

### 3.5 Casos ambíguos → rótulo `incerto`

Quando a informação disponível não permite decidir com confiança (ex.: descrição incompleta que omite variante relevante, marca regional desconhecida sem correspondência clara no dicionário), o par recebe rótulo transitório `incerto` e é adjudicado por consulta ao dicionário canônico oficial ou, quando necessário, aos pesquisadores do projeto ALTA. Pares `incerto` não resolvidos **não integram** o conjunto de teste final.

**`sem_entrada` (só na amostra cega, Seção 2.1):** o produto é descrito de forma clara, mas nenhuma entrada do dicionário serve (por exemplo, a categoria não existe no dicionário, ou é marca própria declarada, que não casa com entrada genérica). É diferente de `incerto`: o produto está claro, quem falta é a entrada. Esses produtos ficam fora do cálculo do recall e são contados à parte, o que também mostra a cobertura do dicionário.

## 4. Procedimento de confiabilidade (teste-reteste)

1. Um subconjunto correspondente a **pelo menos 50% do conjunto de teste** é selecionado aleatoriamente.
2. Após intervalo **≥ 7 dias** da anotação original, o anotador reanota esse subconjunto **sem acesso aos rótulos da primeira passada**.
3. Calcula-se o Cohen's Kappa entre as duas passadas.
4. Faixa desejável: **Kappa ≥ 0,75**. Valores abaixo disso indicam necessidade de revisão das regras da Seção 3 (provável fonte: regras ambíguas ou mal-aplicadas) antes de finalizar o conjunto de teste.

Não haverá segundo anotador (decisão do autor, 2026-10-31; ADR-0005 mantido): a confiabilidade é só intra-anotador, e a limitação já está declarada em `main.tex` §4.1. O Kappa é calculado **por tipo de par**, porque as regras diferem.

## 5. Registro e versionamento

Cada par anotado é registrado com: id do par, texto de origem A, texto de origem B, **tipo de par** (`produto_canonico` ou `produto_produto`), **origem** (`teste` ou `amostra_cega`), tamanho/unidade de cada lado (metadado), rótulo, timestamp da anotação, e flag de pertencimento ao subconjunto de teste-reteste. O arquivo de anotações é versionado no repositório (`dados/processados/anotacoes.csv` ou equivalente), nunca editado retroativamente sem registro de mudança.

O arquivo de anotação **nunca** contém as colunas `codg_item`, `desc_ref` e `match_score` (ADR-0010/0011), e nenhum par de teste é gerado ou rotulado por gerador ou LLM (ADR-0004, emendado pelo ADR-0013).

## 6. Exemplos de referência rápida

Exemplos ilustrativos, não são pares reais da base.

```
PRODUTO x ENTRADA CANÔNICA  (decide categoria e variante; marca e tamanho não contam)
MATCH:
  "ARROZ MARCA X BRANCO 1KG"      <-> ARROZ BRANCO
  "ARROZ MARCA Y TIPO 1 BRANCO 5KG" <-> ARROZ BRANCO     (tamanho e marca não decidem)
NÃO-MATCH:
  "ARROZ MARCA X INTEGRAL 1KG"    <-> ARROZ BRANCO       (variante)
  "FEIJAO CARIOCA MARCA X 1KG"    <-> ARROZ BRANCO       (categoria)
  "LEVE 3 PAGUE 2 ARROZ MARCA X 1KG" <-> ARROZ BRANCO    (kit/promoção)
  "ARROZ [MARCA PRÓPRIA] BRANCO 1KG" <-> ARROZ BRANCO    (marca própria)

PRODUTO x PRODUTO  (decide SKU: marca e tamanho contam)
MATCH:
  "LEITE INTEGRAL ITALAC 1L"      <-> "LT ITALAC INTEGRAL 1000ML"
  "OLEO SOJA LIZA 900ML"          <-> "OLEO COMP SOJA LIZA 0,9L"
  "BISCOITO MARIA BAUDUCCO 200G"  <-> "BISC M BAUDUCCO 200GR"
NÃO-MATCH:
  "LEITE ITALAC INTEGRAL 1L"      <-> "LEITE ITALAC DESNATADO 1L"   (variante)
  "LEITE TIPO A [PRÓPRIA] 1L"     <-> "LEITE ITALAC 1L"             (marca distinta)
  "LEVE 3 PAGUE 2 BISCOITO X"     <-> "BISCOITO X 200G"             (unidade de compra)
  "LEITE ITALAC 500ML"            <-> "LEITE ITALAC 1L"             (tamanho)
  "ARROZ MARCA X BRANCO 1KG"      <-> "ARROZ MARCA X BRANCO 5KG"    (tamanho)

INCERTO (adjudicar):
  "ARROZ MARCA X 5KG" (sem variante especificada) <-> ARROZ BRANCO  (produto × canônico)
  "LEITE ITALAC 1L" (sem variante especificada)   <-> "LEITE ITALAC DESNATADO 1L"  (produto × produto)
```

---

*Este documento é referenciado na Seção 4.1 da proposta de TCC e deve ser atualizado sempre que uma regra for adicionada ou alterada. Mudanças de regra depois que a anotação começar exigem registro de mudança e, se afetarem pares já anotados, reanotação dos afetados.*
