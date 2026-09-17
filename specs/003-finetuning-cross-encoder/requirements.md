# Spec 003: Fine-tuning do Cross-Encoder

**Script correspondente:** `scripts/05_finetuning.py`
**ADRs relacionados:** 0001, 0002, 0003, 0009

## Objetivo
Fine-tuning supervisionado do LLaMA 3.2 3B para classificação binária de pares produto/produto ou produto/canônico.

## Requisitos funcionais
1. LoRA em bf16, sem quantização de 4 bits (ADR-0003) — verificar VRAM disponível no início da execução; se inferior ao documentado (48–141 GB), acionar plano de contingência (ADR-0009) antes de prosseguir.
2. Formatação dos pares de treino (spec 001) como entrada do modelo — mesmo formato usado depois na avaliação (spec 002/004).
3. Mineração de negativos difíceis a partir dos pares de treino.
4. Tracking de experimentos via uma única ferramenta (W&B ou MLflow — decidir e manter consistente em todo o projeto).

## Requisitos não funcionais
- Seeds fixas; configs de hiperparâmetros versionadas (YAML/Hydra), não hardcoded no script.
- Checkpoints e curvas de treino registrados de forma reprodutível.

## Critérios de aceite
- [ ] Pipeline de treino executa de ponta a ponta em um subconjunto pequeno antes do treino completo (smoke test).
- [ ] Modelo treinado avaliado com o mesmo harness da spec 002 (nenhum código de métrica duplicado).
- [ ] Configuração de treino registrada de forma que o experimento seja reproduzível a partir do config sozinho.
