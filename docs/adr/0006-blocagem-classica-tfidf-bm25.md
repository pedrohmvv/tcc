# ADR-0006: Blocagem via TF-IDF/BM25 clássico

**Status:** Aceito

## Contexto
O Cross-Encoder (ADR-0001) tem custo de inferência O(n²) sobre pares (produto × ~1.500 entradas do dicionário canônico). É necessário reduzir o espaço de candidatos antes de pontuar cada par.

## Decisão
Blocagem via TF-IDF ou BM25 sobre o dicionário canônico, reaproveitando os mesmos métodos já implementados como baselines (spec 002). Para cada produto de entrada, os k candidatos mais similares são recuperados por similaridade lexical; o Cross-Encoder pontua cada par (produto, candidato).

## Consequências
- Blocagem é filtro lexical clássico, **não** uma arquitetura Bi-Encoder aprendida — não contradiz o ADR-0001 (a "formulação Cross-Encoder" refere-se ao modelo de decisão, não ao pipeline de produção completo).
- Custo zero adicional: reaproveita infraestrutura de baseline já planejada.
- Recall@K mede se o match verdadeiro está entre os k candidatos retornados pela blocagem, após o reranqueamento do Cross-Encoder; MRR é calculado sobre a posição do match verdadeiro nessa lista.
- A blocagem impõe um teto de recall que o Cross-Encoder não recupera sozinho — deve ser quantificado e reportado separadamente (recall da blocagem isolada, antes do reranqueamento).
- Extensão futura: blocagem neural (embeddings aprendidos) é a porta de entrada natural para o Bi-Encoder mencionado como trabalho futuro (ADR-0001).

## Alternativas consideradas
- **Blocagem por embeddings genéricos (sem fine-tuning):** já é um dos baselines avaliados (spec 002); não descartado como comparação, mas não é o método de blocagem de produção deste TCC.
