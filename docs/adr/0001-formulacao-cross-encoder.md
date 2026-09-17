# ADR-0001: Formulação como Cross-Encoder único

**Status:** Aceito

## Contexto
Três direções candidatas para a tarefa de EM: Cross-Encoder (classificação binária de pares), Bi-Encoder (embeddings + ANN) e híbrido (retrieval + reranking). Execução é individual, 16 semanas, dedicação parcial.

## Decisão
Adotar exclusivamente a formulação Cross-Encoder. Bi-Encoder e arquitetura híbrida ficam fora do escopo deste TCC.

## Consequências
- Escopo fechável no prazo com uma única arquitetura avaliada em profundidade.
- Custo de inferência O(n²) do Cross-Encoder é mitigado por uma etapa de blocagem clássica (ver ADR-0006), não por um encoder aprendido.
- Avaliação simplificada: um único modelo de decisão a comparar contra baselines.
- Bi-Encoder e híbrido tornam-se extensão natural para pós-graduação (ver Seção "Trabalhos Futuros" da proposta).

## Alternativas consideradas
- **Bi-Encoder puro:** mais escalável, mas exige estratégia de hard negative mining e é mais difícil de avaliar com rigor no prazo disponível.
- **Híbrido (retrieval+reranking neural):** melhor trade-off precisão/escalabilidade, mas maior complexidade de implementação — inviável para execução solo em 16 semanas.
