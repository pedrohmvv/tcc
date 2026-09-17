---
name: protocolo-anotacao-em
description: Regras de decisão match/não-match para Entity Matching de produtos de supermercado. Use ao escrever código de suporte à anotação, validar rótulos, ou gerar exemplos de casos-limite.
---

# Protocolo de anotação de Entity Matching

Fonte completa e autoritativa: `docs/protocolo_anotacao.md`. Este skill resume as regras para uso rápido em código; em caso de dúvida ou conflito, o documento completo prevalece.

## Regra geral
Dois itens são **match** se, e somente se, referem-se ao mesmo produto físico comercializável — mesma composição, marca, variante e (condicional, ver abaixo) mesmo tamanho.

## Match
- Abreviação/truncamento/inversão de ordem sem mudança semântica.
- Ruído tipográfico de PDV.
- Unidade equivalente expressa de forma diferente (0,9L = 900ML), quando a equivalência é numérica exata.

## Não-match
- Mesma marca, variante de composição diferente (integral vs. desnatado).
- Marca própria (private label) vs. marca nacional equivalente.
- Kit/promoção vs. unidade avulsa.
- Mesma marca, categoria de produto diferente.

## Regra condicional (tamanho/unidade) — `[DECISÃO PENDENTE]`
Depende da granularidade do dicionário canônico:
- Entrada por SKU/tamanho → tamanhos diferentes = não-match.
- Entrada por produto genérico → tamanhos diferentes = match (se marca/variante coincidem).

Código de anotação/validação deve suportar recalcular sob as duas regras até a definição (registrar tamanho como metadado do par, não descartar).

## Casos incertos
Rótulo transitório `incerto`, adjudicado por consulta ao dicionário canônico oficial. Nunca entram no conjunto de teste final sem resolução.

## Confiabilidade
Anotador único → teste-reteste, não Kappa inter-anotador (ADR-0005). Ver `docs/protocolo_anotacao.md` Seção 4 para o procedimento completo.
