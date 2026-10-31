---
name: reprodutibilidade-ml
description: Convenções de reprodutibilidade e engenharia de ML para os scripts do pipeline (scripts/01 a 06). Use ao escrever, revisar ou depurar qualquer script Python do projeto.
---

# Reprodutibilidade e engenharia de ML

## Regras inegociáveis
- Seed fixa em toda operação estocástica: particionamento de dados, geração sintética, inicialização de treino, shuffling.
- Hiperparâmetros e configurações vivem em YAML versionado, nunca hardcoded dentro do script Python.
- MLflow é a ferramenta de tracking de experimentos (decidido — `pyproject.toml` já traz `mlflow>=2.14`) — usar em todos os scripts de 04 a 06, sem misturar com outra ferramenta.
- Dependências travadas via `pyproject.toml` + `uv.lock` (o template usa `uv`) — nunca instalar pacote ad-hoc sem registrar.

## Split e vazamento de dados
- Particionamento sempre **estratificado por produto canônico**, e sempre **antes** de qualquer geração sintética ou aumentação (ver ADR-0004, spec 001). Para os dados da TAIL (ADR-0013), a unidade de partição é o **grupo de título original** (original, variantes e positivos ligados), com assert de que nenhum grupo cai em mais de uma partição e de que nenhum título do benchmark TAIL (nem quase-duplicata) está no treino ou na validação.
- **Nunca** usar o Dataset Generator (Dharma) **nem qualquer outro gerador ou LLM** (`attack_augmentation` da TAIL, LLM-as-judge, predições de LLM) para gerar ou rotular o conjunto de teste ou de validação (ADR-0004/0013). Isso é a regra mais importante do projeto: violá-la invalida toda avaliação subsequente. O Dataset Generator está suspenso (D-5): não chamar até nova decisão.
- Nada da TAIL é versionado, redistribuído ou publicado sem autorização escrita (ADR-0013). `invoice-data-normalizer/` está no `.gitignore`.
- Antes de rodar qualquer script de treino, validar programaticamente (assert, não revisão manual) que nenhum produto do teste aparece na base de geração de treino.

## Harness de avaliação
- Código de cálculo de métricas escrito uma vez (spec 002) e reutilizado sem duplicação nas specs 003 e 004.
- Blocagem (TF-IDF/BM25, ADR-0006) é a mesma para baselines e para o Cross-Encoder fine-tuned — nunca comparar métodos com blocagens diferentes.

## Checkpoints e logging
- Checkpoints de modelo e curvas de treino salvos de forma versionada, associados ao config que os gerou.
- Todo experimento deve ser reproduzível a partir do config + seed sozinhos, sem depender de estado implícito do ambiente.
