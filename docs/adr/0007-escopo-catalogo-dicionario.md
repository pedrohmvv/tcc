# ADR-0007: Escopo delimitado à subtarefa catálogo-dicionário

**Status:** Aceito

## Contexto
EM neste projeto tem duas subtarefas: (1) matching intra-base (mesmo produto entre lojas distintas) e (2) matching catálogo-dicionário (produto da base → entrada canônica). O parecer do orientador (v2) apontou ambiguidade sobre qual seria o foco.

## Decisão
Foco no matching catálogo-dicionário. A subtarefa intra-base é resolvida como consequência lógica: se dois produtos de lojas diferentes mapeiam à mesma entrada canônica, são transitivamente o mesmo produto — sem pipeline de matching separado. Uma fatia suplementar de ~50–100 pares produto-produto (sem dicionário) valida empiricamente que o mesmo Cross-Encoder generaliza a essa subtarefa, sem retreinamento.

## Consequências
- O Cross-Encoder classifica pares (produto, entrada canônica) e (produto, produto) indistintamente — mesmo modelo, sem custo de retreino para cobrir os dois casos.
- **Limitação reconhecida:** a inferência transitiva herda o erro de cada matching individual — se o modelo erra o mapeamento de A ou de B ao dicionário, o match inferido entre A e B herda esse erro. Isso deve ser mencionado no TCC como limitação, não escondido.
- Avaliação plena da subtarefa intra-base em escala (incluindo blocagem sem dicionário) fica como trabalho futuro — não é o mesmo que "não testar" (a fatia suplementar de validação garante evidência empírica preliminar).

## Alternativas consideradas
- **Duas avaliações completas e independentes** (catálogo-dicionário + intra-base em escala): rejeitada por custo de anotação e de blocagem sem dicionário, incompatível com o prazo de 16 semanas solo.
