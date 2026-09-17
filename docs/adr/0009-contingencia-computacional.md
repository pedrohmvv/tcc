# ADR-0009: Plano de contingência computacional

**Status:** Aceito

## Contexto
O pipeline de fine-tuning depende da infraestrutura da Dharma-AI (GPU e Dataset Generator). Risco de indisponibilidade, atraso, ou VRAM inferior ao documentado (ADR-0003).

## Decisão
Duas mitigações, em ordem de preferência:
1. Migração para recursos de nuvem acadêmica ou Google Colab Pro como ambiente alternativo de treino.
2. Redução do modelo-alvo para Gemma 2 2B (candidato secundário, ADR-0002), que demanda menos VRAM.

## Consequências
- Nenhuma mudança de pipeline necessária se a mitigação (2) for ativada — Gemma 2 2B já tem critérios de seleção próprios documentados (ADR-0002), não exige requalificar o desenho experimental.
- Cronograma permanece viável sob qualquer uma das duas mitigações, sem necessidade de cortar a etapa de ablação.
