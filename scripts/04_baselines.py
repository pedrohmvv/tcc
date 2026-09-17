#!/usr/bin/env python3
"""
04_baselines.py — Baselines clássicos e zero-shot (spec 002)
================================================================

Spec: specs/002-baselines-classicos/requirements.md
ADRs: 0002 (LLaMA 3.2 3B), 0006 (blocagem TF-IDF/BM25), 0008 (McNemar)

Objetivo:
    Estabelecer o piso de comparação obrigatório antes de qualquer modelo
    especializado: TF-IDF, BM25, Levenshtein, Jaccard, embeddings genéricos
    e LLaMA 3.2 3B zero-shot, todos sobre o mesmo conjunto de teste e com o
    mesmo harness de avaliação (reutilizado pelas specs 003/004).

Entradas:
    dados/processados/{candidatos_blocagem,teste}.parquet (spec 001)

Saídas (esperadas, ver spec 002):
    resultados/metricas/baselines_comparacao.csv

Status: esqueleto — implementação pendente (ver spec 002 e skill
avaliacao-baselines).

Uso:
    uv run python scripts/04_baselines.py
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
DADOS_PROCESSADOS = Path("dados/processados")
RESULTADOS_METRICAS = Path("resultados/metricas")

BASELINES = ("tfidf", "bm25", "levenshtein", "jaccard", "embeddings_genericos", "llama_zero_shot")


def rodar_baselines_classicos(diretorio_processados: Path) -> None:
    """TF-IDF, BM25, Levenshtein, Jaccard, embeddings genéricos — ADR-0006."""
    raise NotImplementedError("Implementar conforme specs/002-baselines-classicos/requirements.md")


def rodar_llama_zero_shot(diretorio_processados: Path) -> None:
    """LLaMA 3.2 3B zero-shot (mesmo checkpoint-base do fine-tuning) — ADR-0002/0008."""
    raise NotImplementedError("Implementar conforme specs/002-baselines-classicos/requirements.md")


def main() -> None:
    logger.info("Etapa 04 (baselines) ainda não implementada — ver spec 002.")
    rodar_baselines_classicos(DADOS_PROCESSADOS)
    rodar_llama_zero_shot(DADOS_PROCESSADOS)


if __name__ == "__main__":
    main()
