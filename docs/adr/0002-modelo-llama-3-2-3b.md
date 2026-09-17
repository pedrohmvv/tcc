# ADR-0002: LLaMA 3.2 3B como SLM principal

**Status:** Aceito

## Contexto
Três candidatos SLM: Phi-3 Mini (~3,8B, MIT), Gemma 2 2B (Gemma Terms of Use), LLaMA 3.2 3B (Llama Community License). Critérios: tamanho, suporte a português, custo de fine-tuning, licença, documentação. A comparação é restrita à faixa de 2–4B por critério de escala definido a priori (ver Alternativas consideradas): viabilizar a operação continuada do modelo pelo projeto ALTA após o TCC, sem depender de infraestrutura de inferência robusta.

## Decisão
LLaMA 3.2 3B como modelo principal. Gemma 2 2B mantido como candidato secundário / fallback (ver ADR-0009).

## Consequências
- Único dos três a listar explicitamente português entre os idiomas suportados — relevante para descrições de produto em PT-BR.
- Equilibra custo de adaptação (3B) e capacidade; documentação madura reduz atrito no prazo apertado.
- Licença mais restritiva que o MIT do Phi-3 (Llama Community License, cláusula de uso aceitável) — aceitável para uso acadêmico, mas relevante se o projeto evoluir para uso comercial via Dharma-AI.

## Alternativas consideradas
- **Phi-3 Mini:** melhor para raciocínio/contexto longo, irrelevante para pares curtos de produto; fora do escopo principal.
- **Gemma 2 2B:** menor, mais barato — mantido como plano B (ADR-0009), não como principal, por não declarar suporte explícito a PT.
- **Modelos 10B–30B (quantizados e/ou MoE):** tecnicamente viáveis na infraestrutura de treino da Dharma-AI (GPUs de 48–141GB), mas descartados da comparação por dependerem de infraestrutura de inferência robusta incompatível com a operação continuada do modelo pelo projeto ALTA após o encerramento do TCC. O critério de restrição de escala (2–4B) é definido justamente para preservar essa portabilidade, não por limitação de capacidade computacional durante o desenvolvimento.

## Revisão (parecer do avaliador, 2026-08-15)
O parecer da avaliação de TCC I (`docs/parecer/2026-08-15-parecer-avaliador.pdf`) apontou a justificativa da escolha do modelo-base como o ponto mais frágil da proposta, questionando por que só três candidatos de 2–4B foram considerados e por que modelos maiores (10–30B, quantizados/MoE) não entraram na comparação, dado que a infra também os suportaria. Confirmado com o autor o racional: evitar dependência de infraestrutura robusta para preservar a viabilidade de operação continuada pelo projeto ALTA. Decisão **reafirmada sem alteração**; critério de exclusão explicitado acima e em `main.tex`, §4.2.
