# Protocolo de Anotação — Entity Matching de Produtos de Supermercado

**Projeto:** TCC — Entity Matching em Produtos de Supermercado com SLMs Fine-Tuned
**Autor:** Pedro Henrique Medeiros Vieira
**Última atualização:** 2026-08-13
**Status:** `[DECISÃO PENDENTE]` regra de tamanho/unidade depende da granularidade do dicionário canônico (ver Seção 3)

---

## 1. Objetivo

Este documento define as regras operacionais que o anotador (autor) segue para decidir se um par de descrições de produto é `match` ou `não-match`, garantindo que decisões sejam **consistentes, reprodutíveis e auditáveis** — condição necessária para que o teste-reteste (Seção 4.1 da proposta) seja informativo.

## 2. Escopo dos pares anotados

Dois tipos de par são anotados no mesmo esforço (Semanas 3–5):

1. **Produto × Entrada canônica** (核心, ~250–450 pares) — par entre uma descrição bruta da base ALTA e uma entrada do dicionário canônico.
2. **Produto × Produto** (~50–100 pares, fatia suplementar) — par entre duas descrições brutas de lojas diferentes, sem intermediação do dicionário. Usado para validar a generalização do Cross-Encoder à subtarefa intra-base (Seção 1.1 da proposta).

As mesmas regras de decisão (Seção 3) aplicam-se aos dois tipos de par.

## 3. Regras de decisão (match / não-match / incerto)

### 3.1 Regra geral

Dois itens são **match** se, e somente se, referem-se ao **mesmo produto físico comercializável** — mesma composição, mesma marca, mesma variante e (dependendo da granularidade do dicionário — ver 3.4) mesmo tamanho/quantidade.

### 3.2 Casos de MATCH

| Situação | Exemplo | Decisão |
|---|---|---|
| Abreviação/truncamento sem mudança semântica | "LEITE INTEGRAL ITALAC 1L" vs. "LT ITALAC INTEGRAL 1000ML" | **match** |
| Inversão na ordem dos tokens | "OLEO SOJA LIZA 900ML" vs. "OLEO COMP SOJA LIZA 0,9L" | **match** |
| Ruído tipográfico de PDV (letras faltando, sem acento) | "BISCOITO MARIA BAUDUCCO 200G" vs. "BISC M BAUDUCCO 200GR" | **match** |
| Unidade equivalente expressa de forma diferente | "0,9L" vs. "900ML" vs. "900G" (quando a equivalência é numérica exata) | **match** |

### 3.3 Casos de NÃO-MATCH

| Situação | Exemplo | Decisão |
|---|---|---|
| Mesma marca, variante de composição diferente | "LEITE ITALAC INTEGRAL 1L" vs. "LEITE ITALAC DESNATADO 1L" | **não-match** |
| Marca própria (private label) vs. marca nacional equivalente | "LEITE TIPO A [MARCA PRÓPRIA] 1L" vs. "LEITE ITALAC 1L" | **não-match** — são produtos/entidades distintas, mesmo se funcionalmente similares |
| Kit/promoção vs. unidade avulsa | "LEVE 3 PAGUE 2 BISCOITO X" vs. "BISCOITO X 200G" | **não-match** — unidade de compra diferente |
| Mesma marca, categoria de produto diferente | "ITALAC LEITE 1L" vs. "ITALAC IOGURTE 170G" | **não-match** |
| Tamanho/unidade diferente (**se dicionário for granular por SKU — ver 3.4**) | "LEITE ITALAC 500ML" vs. "LEITE ITALAC 1L" | **não-match** (nesse regime) |

### 3.4 Regra condicional — tamanho e unidade

`[DECISÃO PENDENTE — resolver ao checar o dicionário canônico]`

- **Se o dicionário canônico tem uma entrada por tamanho/SKU** (ex.: "Leite Italac Integral 1L" e "Leite Italac Integral 500ml" são entradas distintas): produtos de tamanhos diferentes são **não-match**, mesmo que marca/variante coincidam.
- **Se o dicionário canônico tem uma entrada por produto genérico** (ex.: "Leite Italac Integral" cobre todos os tamanhos): produtos de tamanhos diferentes são **match**, desde que marca/variante coincidam.

Até a definição, o anotador registra o tamanho como metadado do par e aplica **ambas as regras em paralelo** (duas colunas de rótulo), permitindo recalcular o conjunto quando a decisão for tomada, sem re-anotar do zero.

### 3.5 Casos ambíguos → rótulo `incerto`

Quando a informação disponível não permite decidir com confiança (ex.: descrição incompleta que omite variante relevante, marca regional desconhecida sem correspondência clara no dicionário), o par recebe rótulo transitório `incerto` e é adjudicado por consulta ao dicionário canônico oficial ou, quando necessário, aos pesquisadores do projeto ALTA. Pares `incerto` não resolvidos **não integram** o conjunto de teste final.

## 4. Procedimento de confiabilidade (teste-reteste)

1. Um subconjunto correspondente a **pelo menos 50% do conjunto de teste** é selecionado aleatoriamente.
2. Após intervalo **≥ 7 dias** da anotação original, o anotador reanota esse subconjunto **sem acesso aos rótulos da primeira passada**.
3. Calcula-se o Cohen's Kappa entre as duas passadas.
4. Faixa desejável: **Kappa ≥ 0,75**. Valores abaixo disso indicam necessidade de revisão das regras da Seção 3 (provável fonte: regras ambíguas ou mal-aplicadas) antes de finalizar o conjunto de teste.

## 5. Registro e versionamento

Cada par anotado é registrado com: id do par, texto de origem A, texto de origem B, tipo de par (produto×canônico ou produto×produto), tamanho/unidade de cada lado (metadado), rótulo, rótulo da regra alternativa quando aplicável (Seção 3.4), timestamp da anotação, e flag de pertencimento ao subconjunto de teste-reteste. O arquivo de anotações é versionado no repositório (`dados/processados/anotacoes.csv` ou equivalente), nunca editado retroativamente sem registro de mudança.

## 6. Exemplos de referência rápida

```
MATCH:
  "LEITE INTEGRAL ITALAC 1L"      <-> "LT ITALAC INTEGRAL 1000ML"
  "OLEO SOJA LIZA 900ML"          <-> "OLEO COMP SOJA LIZA 0,9L"
  "BISCOITO MARIA BAUDUCCO 200G"  <-> "BISC M BAUDUCCO 200GR"

NÃO-MATCH:
  "LEITE ITALAC INTEGRAL 1L"      <-> "LEITE ITALAC DESNATADO 1L"   (variante)
  "LEITE TIPO A [PRÓPRIA] 1L"     <-> "LEITE ITALAC 1L"             (marca distinta)
  "LEVE 3 PAGUE 2 BISCOITO X"     <-> "BISCOITO X 200G"             (unidade de compra)
  "LEITE ITALAC 500ML"           <-> "LEITE ITALAC 1L"             (tamanho, regime SKU-level)

INCERTO (adjudicar):
  "LEITE ITALAC 1L" (sem variante especificada) <-> "LEITE ITALAC DESNATADO 1L"
```

---

*Este documento é referenciado na Seção 4.1 da proposta de TCC e deve ser atualizado sempre que uma regra for adicionada, alterada ou a pendência da Seção 3.4 for resolvida.*
