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

## Regra de tamanho/unidade — resolvida
O dicionário canônico tem uma entrada por **produto genérico** (sem marca, sem tamanho). Logo, para pares (produto, entrada canônica): **tamanhos diferentes são match**, desde que a categoria/variante coincida. Não há mais duas regras alternativas a suportar em código — registrar tamanho/unidade como metadado do par continua obrigatório (ruído de PDV), mas não afeta mais a decisão de match.

`[NOTA]` A regra geral e as regras de não-match baseadas em marca acima assumem entradas canônicas com marca, o que não é o caso do dicionário real — essa revisão de mérito ainda está pendente (ver `docs/protocolo_anotacao.md` §3.4).

## Casos incertos
Rótulo transitório `incerto`, adjudicado por consulta ao dicionário canônico oficial. Nunca entram no conjunto de teste final sem resolução.

## Confiabilidade
Anotador único → teste-reteste, não Kappa inter-anotador (ADR-0005). Ver `docs/protocolo_anotacao.md` Seção 4 para o procedimento completo.
