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

## Emenda (2026-10-31): como medir o recall e como escolher k
Não reverte a decisão acima. Detalha a medição que a consequência da linha 15 já exigia, depois de verificar que ela não pode ser feita só com os pares do teste: se o autor anotar apenas os candidatos que a blocagem devolveu, o que a blocagem perde nunca aparece, e o recall sai otimista (mesmo limite das métricas condicionadas ao candidato do artigo da TAIL).

- **Amostra cega:** ~50 produtos sorteados (seed fixa) da base limpa, **deduplicados por texto normalizado** (critério C2 de `docs/limpeza_dados.md`). O autor indica a entrada correta do dicionário **sem ver a lista de candidatos**, ou registra `sem_entrada` (ver `docs/protocolo_anotacao.md` §2.1 e §3.5). O recall da blocagem isolada é calculado sobre os produtos que têm entrada.
- **Varredura de k:** 1, 5, 10, 20, 50 e 100.
- **Método:** TF-IDF e BM25 são avaliados e reportados; a blocagem oficial é o de maior recall na amostra cega. A escolha é feita **na amostra cega, nunca nos pares do teste**.
- **Congelamento:** o k escolhido e o método ficam em config YAML versionada e são congelados **antes** de gerar os pares do teste produto × dicionário. Baselines e Cross-Encoder usam exatamente essa blocagem (skill `avaliacao-baselines`).
- **Escopo:** esta emenda cobre a blocagem produto × dicionário. A geração de candidatos produto × produto (entre lojas) é tratada à parte (tarefa 1.2b do plano) e não faz parte desta decisão. Pelo ADR-0014, a 1.2b é a fatia principal.

## Alternativas consideradas
- **Medir o recall só nos pares anotados do teste:** rejeitada, por ser condicionada ao candidato e otimista.
- **Blocagem por embeddings genéricos (sem fine-tuning):** já é um dos baselines avaliados (spec 002); não descartado como comparação, mas não é o método de blocagem de produção deste TCC.
