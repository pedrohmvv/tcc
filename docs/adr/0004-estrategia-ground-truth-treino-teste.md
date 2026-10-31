# ADR-0004: Separação de origem dos rótulos — treino via Generator, teste manual independente

**Status:** Aceito — CRÍTICO, não reabrir sem revisão extensa. **Emendado pelo ADR-0013:** a proibição de gerador no teste passa a valer para qualquer gerador ou LLM (Dataset Generator, `attack_augmentation` da TAIL, LLM-as-judge, predições de LLM), e entram novas fontes de treino (TAIL) e um teste externo exploratório. O teste principal continua manual, sobre a ALTA. **Emendado também pelo ADR-0014:** o tamanho do teste (~300–500 pares) era a estimativa para produto × dicionário; o tamanho por fatia está em aberto (produto × produto é a principal). A proibição de gerador/LLM no teste e na validação não muda.

## Contexto
Ausência total de ground truth anotado no início do projeto (risco primário do TCC). A Dharma-AI disponibiliza um Dataset Generator movido inteiramente a LLM (todo o pipeline de geração, avaliação e extensão de dados passa por chamadas de LLM — não há caminho no código que gere dados sem LLM).

## Decisão
- **Treino:** construído via Dataset Generator (paráfrases/variações do dicionário canônico real) + supervisão distante + aumentação sintética por perturbação de tokens.
- **Teste:** padrão-ouro de ~300–500 pares, anotado manualmente pelo autor, diretamente sobre dados reais do ALTA, **independente do Dataset Generator**.
- Produtos que compõem o teste são removidos da base que alimenta a geração de treino, com a partição por produto canônico aplicada **antes** de qualquer geração.

## Consequências
- Evita avaliação circular: se o teste fosse produzido pela mesma ferramenta do treino, mediria aderência à distribuição do gerador, não capacidade de resolver o problema real.
- Volume de teste é limitado pelo esforço manual (~300–500 pares), menor do que seria possível com geração 100% automática.
- **Nunca usar o Dataset Generator para gerar ou rotular pares de teste — em nenhuma circunstância, mesmo sob pressão de prazo.** Violar isso invalida a avaliação inteira do TCC.
- O dicionário canônico usado como ancoragem da supervisão distante é o real do ALTA — o Generator só parafraseia/varia suas entradas, nunca substitui os dados reais como fonte de rótulo do teste.

## Alternativas consideradas
- **Teste também gerado pelo Generator:** rejeitado — reabre a circularidade que motivou esta decisão.
- **Anotação manual também para o treino:** inviável no prazo (16 semanas, solo, poucas horas/semana).
