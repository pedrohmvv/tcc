# Spec 003: Fine-tuning do Cross-Encoder

**Script correspondente:** `scripts/05_finetuning.py`
**ADRs relacionados:** 0001, 0002, 0003, 0009, 0013, 0014

## Objetivo
Fine-tuning supervisionado do LLaMA 3.2 3B para classificação binária de pares, com **dois adaptadores LoRA sobre o mesmo checkpoint-base**, um por tipo de par: produto × dicionário e produto × produto (ADR-0013; prioridade das fatias: ADR-0014).

## Requisitos funcionais
1. LoRA em bf16, sem quantização de 4 bits (ADR-0003) — verificar VRAM disponível no início da execução; se inferior ao documentado (48–141 GB), acionar plano de contingência (ADR-0009) antes de prosseguir.
2. Formatação dos pares de treino (spec 001) como entrada do modelo — mesmo formato usado depois na avaliação (spec 002/004), para cada adaptador. Não há marcador de tipo de par: o adaptador define a regra de match.
3. Mineração de negativos difíceis a partir dos pares de treino.
4. Tracking de experimentos via MLflow (decidido — `pyproject.toml` já traz `mlflow>=2.14`), usado de forma consistente em todos os scripts de 04 a 06.
5. **Dois adaptadores, cada um com seus dados e sua config** (YAML por adaptador): (a) produto × dicionário (fatia secundária, ADR-0014), treinado só com dados da ALTA (a TAIL não tem pares produto × dicionário); a fonte desses pares depende da D-5 (Generator suspenso) e precisa estar decidida antes de treinar (só bloqueia este adaptador, o secundário); (b) produto × produto (fatia principal, ADR-0014), treinado com pares da ALTA e da TAIL, com a mistura de fontes definida em config. O orçamento de GPU e de runs é fixado para os dois adaptadores antes de começar.

## Requisitos não funcionais
- Seeds fixas; configs de hiperparâmetros versionadas (YAML/Hydra), não hardcoded no script.
- Checkpoints e curvas de treino registrados de forma reprodutível.

## Critérios de aceite
- [ ] Pipeline de treino executa de ponta a ponta em um subconjunto pequeno antes do treino completo (smoke test).
- [ ] Os dois adaptadores avaliados, cada um na sua fatia, com o mesmo harness da spec 002 (nenhum código de métrica duplicado).
- [ ] Configuração de treino registrada de forma que o experimento seja reproduzível a partir do config sozinho.
