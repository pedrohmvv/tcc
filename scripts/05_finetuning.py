#!/usr/bin/env python3
"""
05_finetuning.py — Fine-tuning LoRA do Cross-Encoder (spec 003)
===================================================================

Spec: specs/003-finetuning-cross-encoder/requirements.md
ADRs: 0001 (Cross-Encoder), 0002 (LLaMA 3.2 3B), 0003 (LoRA bf16, sem
      quantização), 0009 (contingência computacional)

Objetivo:
    Fine-tuning supervisionado do LLaMA 3.2 3B para classificação binária
    de pares produto/produto ou produto/canônico, com LoRA em bf16.

Depende de infraestrutura com GPU (Dharma-AI, 48-141 GB VRAM documentados
em ADR-0003). Se a VRAM disponível for inferior ao documentado, acionar o
plano de contingência do ADR-0009 (Gemma 2 2B / Colab Pro) ANTES de seguir.

Entradas:
    dados/processados/{treino,validacao}.parquet (spec 001)

Saídas (esperadas, ver spec 003):
    modelos/adapter_lora/ (checkpoint do adaptador LoRA)
    Tracking de experimentos: MLflow (decisão do projeto)

Status: esqueleto — implementação pendente (ver spec 003).

Uso:
    uv run python scripts/05_finetuning.py
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
DADOS_PROCESSADOS = Path("dados/processados")
MODELOS = Path("modelos")


def verificar_vram_disponivel() -> None:
    """Verifica VRAM no início da execução; aciona contingência do ADR-0009 se insuficiente."""
    raise NotImplementedError(
        "Implementar conforme specs/003-finetuning-cross-encoder/requirements.md"
    )


def treinar_lora(diretorio_processados: Path, diretorio_modelos: Path) -> None:
    """LoRA em bf16 (ADR-0003) com mineração de negativos difíceis (spec 003)."""
    raise NotImplementedError(
        "Implementar conforme specs/003-finetuning-cross-encoder/requirements.md"
    )


def main() -> None:
    logger.info("Etapa 05 (fine-tuning) ainda não implementada — ver spec 003.")
    verificar_vram_disponivel()
    treinar_lora(DADOS_PROCESSADOS, MODELOS)


if __name__ == "__main__":
    main()
