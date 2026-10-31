---
name: protocolo-anotacao-em
description: Regras de decisão match/não-match para Entity Matching de produtos de supermercado, por tipo de par. Use ao escrever código de suporte à anotação, validar rótulos, ou gerar exemplos de casos-limite.
---

# Protocolo de anotação de Entity Matching

Fonte completa e autoritativa: `docs/protocolo_anotacao.md`. Este skill resume as regras para uso rápido em código; em caso de dúvida ou conflito, o documento completo prevalece. Decisões: ADR-0013 e ADR-0014 (produto × produto é a fatia principal; produto × entrada canônica, a secundária — as regras de cada tipo não mudam).

## Duas regras, uma por tipo de par
Cada par é anotado e validado sob a regra do **seu tipo**, registrado na linha (`produto_canonico` ou `produto_produto`). Nunca aplicar a regra de um tipo ao outro.

| Tipo de par | É match se... | Marca | Tamanho |
|---|---|---|---|
| Produto × entrada canônica | mesma categoria e mesma variante | não decide (exceto marca própria) | não decide |
| Produto × produto | mesmo SKU | decide | decide |

O dicionário canônico tem uma entrada por **produto genérico** (sem marca, sem tamanho). Dois produtos na mesma entrada são da mesma categoria, não necessariamente o mesmo SKU.

## Match (os dois tipos, dentro da regra do tipo)
- Abreviação/truncamento/inversão de ordem sem mudança semântica.
- Ruído tipográfico de PDV.
- Só em produto × produto: unidade equivalente expressa de outra forma (0,9L = 900ML), quando a equivalência é numérica exata.

## Não-match em produto × entrada canônica
- Variante diferente da entrada (integral × branco).
- Categoria diferente.
- Kit/promoção ("LEVE 3 PAGUE 2 ...").
- Marca própria **somente quando o texto da descrição declara** (ex.: "[MARCA PRÓPRIA]"). O conhecimento do anotador sobre as marcas das redes não é usado. Marca própria sem sinal no texto segue as regras gerais.

## Não-match em produto × produto
- Variante de composição diferente com a mesma marca.
- Marca diferente, inclusive marca própria vs. marca nacional.
- Tamanho/unidade diferente (1 kg ≠ 5 kg).
- Kit/promoção vs. unidade avulsa.
- Mesma marca, categoria diferente.

## Metadado
Tamanho/unidade é sempre registrado como metadado do par (ruído de PDV), nos dois tipos, mesmo quando não decide o match.

## Casos incertos
Rótulo transitório `incerto`, adjudicado por consulta ao dicionário canônico oficial. Nunca entram no conjunto de teste final sem resolução.

## Amostra cega (recall da blocagem)
~50 produtos sorteados com seed fixa, anotados **sem ver candidatos**: o autor indica a entrada do dicionário ou `sem_entrada` (produto claro, nenhuma entrada serve; diferente de `incerto`). A linha registra a origem (`teste` ou `amostra_cega`). Ver `docs/protocolo_anotacao.md` §2.1 e ADR-0006 (emenda).

## Confiabilidade
Anotador único → teste-reteste intra-anotador, Kappa calculado **por tipo de par** (ADR-0005). Não haverá segundo anotador. Ver `docs/protocolo_anotacao.md` Seção 4.

## Proibições
Nenhum gerador ou LLM produz ou rotula pares de teste (ADR-0004/0013). O arquivo de anotação nunca contém `codg_item`, `desc_ref` ou `match_score` (ADR-0010/0011).
