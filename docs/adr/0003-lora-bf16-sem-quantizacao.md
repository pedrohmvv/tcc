# ADR-0003: LoRA em bf16, sem quantização de 4 bits

**Status:** Aceito

## Contexto
VRAM real da infraestrutura Dharma-AI documentada: 48 GB (NVIDIA L40S, tier dev) a 141 GB (NVIDIA H200, tier low). Config de teste do ambiente (`default.yml`) usa `load_in_4bit: True`, mas isso não está confirmado como decisão de produto.

## Decisão
Fine-tuning via LoRA em precisão bf16, sem quantização de 4 bits (não QLoRA).

## Consequências
- VRAM disponível é ampla para um modelo de 3B parâmetros — quantização agressiva é desnecessária.
- Preserva maior precisão numérica no ajuste fino, relevante para uma tarefa de classificação fina como EM.
- `[a confirmar oficialmente com o time de plataforma da Dharma-AI]`: se `load_in_4bit: True` no config de teste reflete alguma restrição de produção não documentada, revisar este ADR.

## Alternativas consideradas
- **QLoRA (4-bit):** apropriado quando VRAM é o gargalo — não é o caso aqui.
